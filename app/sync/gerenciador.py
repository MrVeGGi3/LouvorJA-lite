"""Roda o download em segundo plano, um trabalho por vez, e publica o progresso.

Um trabalho por vez de propósito: o servidor oficial é o mesmo para o banco e para a mídia, e duas
sessões concorrentes só disputariam a mesma banda enquanto multiplicam as chances de o servidor
derrubar a conexão. Pedir um segundo download com um em andamento devolve 409, não uma fila.

Parar no meio é seguro por construção: `Sessao.baixar` escreve num `.part` e só promove o arquivo
quando o tamanho confere, então o cancelamento nunca deixa um arquivo truncado se passando por
completo — e o próximo download retoma do byte exato onde parou.
"""

import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app import config
from app.db.arquivos import caminho_local, caminho_remoto
from app.sync import catalogo, louvorja_api, midia

# De quantos em quantos arquivos o `_download_state.json` é regravado. Gravar a cada arquivo
# castigaria o pendrive sem necessidade; 25 é o intervalo que o script de linha de comando já usava.
INTERVALO_ESTADO = 25

# Pausa entre arquivos, para não martelar o servidor.
PAUSA_ENTRE_ARQUIVOS = 0.1


class JaEmAndamento(RuntimeError):
    """Já existe um download rodando — o chamador deve devolver 409."""


@dataclass
class Progresso:
    estado: str = "ocioso"          # ocioso | rodando | concluido | cancelado | erro
    tarefa: str = ""                # banco | midia | arquivo
    escopo: str = ""                # "Hinário Adventista", "catálogo inteiro", nome do arquivo
    total_arquivos: int = 0
    arquivos_prontos: int = 0
    total_bytes: int = 0
    bytes_prontos: int = 0
    arquivo_atual: str = ""
    taxa_bps: float = 0.0
    segundos_restantes: float | None = None
    falhas: list[dict] = field(default_factory=list)
    mensagem: str = ""
    # Incrementa a cada mudança. É o que o SSE observa para saber que há novidade — bem mais
    # barato do que comparar o dicionário inteiro a cada 500 ms.
    versao: int = 0


class Gerenciador:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._progresso = Progresso()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        # Ponto de injeção: os testes trocam isto por uma sessão falsa para não tocar a rede.
        self.fabrica_sessao = louvorja_api.Sessao

    # -- leitura ------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            dados = asdict(self._progresso)
        dados["falhas"] = list(dados["falhas"])
        return dados

    @property
    def rodando(self) -> bool:
        with self._lock:
            return self._progresso.estado == "rodando"

    # -- escrita ------------------------------------------------------------

    def _atualizar(self, **campos) -> None:
        with self._lock:
            for chave, valor in campos.items():
                setattr(self._progresso, chave, valor)
            self._progresso.versao += 1

    def cancelar(self) -> None:
        self._parar.set()
        if self.rodando:
            self._atualizar(mensagem="Parando…")

    def _iniciar(self, tarefa: str, escopo: str, trabalho) -> None:
        with self._lock:
            if self._progresso.estado == "rodando":
                raise JaEmAndamento("já existe um download em andamento")
            self._parar.clear()
            self._progresso = Progresso(
                estado="rodando",
                tarefa=tarefa,
                escopo=escopo,
                versao=self._progresso.versao + 1,
            )
            self._thread = threading.Thread(target=self._executar, args=(trabalho,), daemon=True)
            self._thread.start()

    def _executar(self, trabalho) -> None:
        try:
            trabalho()
        except louvorja_api.ErroDeConexao as erro:
            self._atualizar(estado="erro", mensagem=f"Não consegui falar com o servidor: {erro}")
        except catalogo.ErroDeCatalogo as erro:
            self._atualizar(estado="erro", mensagem=str(erro))
        except Exception as erro:  # noqa: BLE001 — o thread não pode morrer calado
            self._atualizar(estado="erro", mensagem=f"Falhou: {erro}")
        finally:
            midia.invalidar_resumo()

    # -- trabalhos ----------------------------------------------------------

    def iniciar_banco(self) -> None:
        """Baixa (ou atualiza) o database.db do servidor oficial."""

        def trabalho() -> None:
            self._atualizar(arquivo_atual="database.db", total_arquivos=1)
            info = catalogo.baixar_banco_do_servidor(config.DB_PATH)
            faltando = info.get("tables_missing") or []
            self._atualizar(
                estado="concluido",
                arquivos_prontos=1,
                arquivo_atual="",
                mensagem=(
                    f"Catálogo atualizado, mas faltam tabelas: {', '.join(faltando)}"
                    if faltando else "Catálogo atualizado."
                ),
            )

        self._iniciar("banco", "catálogo de hinos", trabalho)

    def iniciar_midia(self, album: int | None = None, only: str = "all", escopo: str = "") -> None:
        """Baixa os arquivos que faltam — do catálogo inteiro ou de um álbum."""
        dest = config.DATA_DIR
        db_path = config.DB_PATH

        def trabalho() -> None:
            arquivos = midia.listar_arquivos(db_path, album, only)
            if not arquivos:
                self._atualizar(
                    estado="erro",
                    mensagem="Nada a baixar — atualize o catálogo de hinos primeiro.",
                )
                return
            self._baixar_lista(midia.pendentes(dest, arquivos), dest, len(arquivos))

        self._iniciar("midia", escopo or ("catálogo inteiro" if album is None else f"álbum {album}"), trabalho)

    def iniciar_arquivo(self, id_file: int) -> None:
        """Baixa um arquivo avulso — o 'Baixar agora' do player."""
        dest = config.DATA_DIR
        db_path = config.DB_PATH

        def trabalho() -> None:
            linha = midia.obter_arquivo(db_path, id_file)
            if linha is None:
                self._atualizar(estado="erro", mensagem="Arquivo não encontrado no catálogo.")
                return
            self._atualizar(escopo=linha["file_name"])
            self._baixar_lista([linha], dest, 1)

        self._iniciar("arquivo", "", trabalho)

    # -- laço de download ---------------------------------------------------

    def _baixar_lista(self, pendentes: list, dest: Path, total_no_catalogo: int) -> None:
        total_bytes = sum(a["size"] for a in pendentes)
        self._atualizar(total_arquivos=len(pendentes), total_bytes=total_bytes)

        if not pendentes:
            self._atualizar(estado="concluido", mensagem="Tudo já está em disco.")
            return

        baixados = 0
        bytes_baixados = 0
        falhas: list[dict] = []
        inicio = time.monotonic()

        with self.fabrica_sessao() as sessao:
            for i, a in enumerate(pendentes, 1):
                if self._parar.is_set():
                    midia.salvar_estado(dest, total_no_catalogo, baixados, falhas)
                    self._atualizar(
                        estado="cancelado",
                        arquivo_atual="",
                        mensagem=f"Parado — {baixados} de {len(pendentes)} arquivos baixados.",
                    )
                    return

                remoto = caminho_remoto(a["type"], a["dir"], a["file_name"])
                destino = caminho_local(dest, a["type"], a["dir"], a["file_name"])
                self._atualizar(arquivo_atual=a["file_name"])

                try:
                    bytes_baixados += sessao.baixar(remoto, destino, a["size"])
                    baixados += 1
                except louvorja_api.ErroDeConexao as erro:
                    falhas.append(
                        {"id_file": a["id_file"], "arquivo": a["file_name"], "erro": str(erro)}
                    )

                decorrido = time.monotonic() - inicio
                taxa = bytes_baixados / decorrido if decorrido else 0
                self._atualizar(
                    arquivos_prontos=baixados,
                    bytes_prontos=bytes_baixados,
                    taxa_bps=taxa,
                    segundos_restantes=(total_bytes - bytes_baixados) / taxa if taxa else None,
                    falhas=list(falhas),
                )

                if i % INTERVALO_ESTADO == 0:
                    midia.salvar_estado(dest, total_no_catalogo, baixados, falhas)
                    midia.invalidar_resumo()
                time.sleep(PAUSA_ENTRE_ARQUIVOS)

        midia.salvar_estado(dest, total_no_catalogo, baixados, falhas)
        self._atualizar(
            estado="concluido",
            arquivo_atual="",
            segundos_restantes=0,
            mensagem=(
                f"{baixados} arquivos baixados. {len(falhas)} falharam — tente de novo para retomar."
                if falhas else f"Pronto — {baixados} arquivos baixados."
            ),
        )


# Uma instância só, compartilhada pelas rotas.
gerenciador = Gerenciador()
