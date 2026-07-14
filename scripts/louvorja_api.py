"""Cliente do servidor de mídia do LouvorJA, transcrito do app oficial (fmAtualiza.pas).

O acesso é em dois passos: `/params?type=env` devolve um token JWT de curta duração, e esse
token autoriza uma conexão (FTP ou HTTPS) de onde os arquivos são baixados. O token gravado em
disco pelo app Desktop expira — por isso ele é sempre rebuscado, nunca cacheado.
"""

import base64
import ftplib
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

URL_PARAMS = "https://api.louvorja.com.br/params?type=env"
API_TOKEN = "02@v2nFB2Dc"
USER_AGENT = "LouvorJA/26.7"
TIMEOUT = 30


class ErroDeConexao(RuntimeError):
    pass


@dataclass
class Conexao:
    host: str
    root: str
    port: int
    username: str
    password: str

    @property
    def is_ftp(self) -> bool:
        # Mesma regra do original (fmAtualiza.pas:140-142): é FTP se a URL declara ftp://, ou se
        # não é http e a porta é a do FTP (ou nem foi informada).
        if self.host.startswith("ftp://"):
            return True
        return not self.host.startswith("http") and self.port in (0, 21)

    @property
    def host_puro(self) -> str:
        return self.host.split("://", 1)[-1].rstrip("/")

    @property
    def base_url(self) -> str:
        base = self.host if "://" in self.host else f"https://{self.host}"
        return base.rstrip("/") + self.root_normalizado

    @property
    def root_normalizado(self) -> str:
        raiz = (self.root or "").replace("\\", "/").strip()
        if not raiz or raiz == "/":
            return ""
        return "/" + raiz.strip("/")


def _get(url: str, token: str | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if token:
        req.add_header("Api-Token", token)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _parse_kv(texto: str) -> dict[str, str]:
    return dict(
        linha.split("=", 1) for linha in texto.splitlines() if "=" in linha
    )


def obter_params() -> dict[str, str]:
    """Busca os parâmetros do servidor, incluindo o `conn_ftp` com um token válido."""
    params = _parse_kv(_get(URL_PARAMS, API_TOKEN).decode("utf-8", "replace"))
    if not params.get("conn_ftp"):
        raise ErroDeConexao("o servidor não devolveu conn_ftp")
    return params


def obter_conexao(params: dict[str, str] | None = None) -> Conexao:
    """Troca o token por credenciais de acesso aos arquivos."""
    params = params or obter_params()
    conn_ftp = params["conn_ftp"]

    dados = (
        f"&lang=pt&version={params.get('pt_version', '')}"
        f"&bin_version={params.get('pt_version', '')}"
        f"&datetime={datetime.now():%Y-%m-%d %H:%M:%S}"
        f"&ip=&directory=louvorja-lite&pc_name=louvorja-lite"
    )
    separador = "&" if "?" in conn_ftp else "?"
    url = (
        f"{conn_ftp}{separador}data="
        f"{urllib.parse.quote(base64.b64encode(dados.encode()).decode())}&lang=pt"
    )

    resposta = _get(url).decode("utf-8", "replace").strip()
    if not resposta:
        raise ErroDeConexao("resposta vazia ao autorizar a conexão")

    try:
        decodificado = base64.b64decode(resposta + "==").decode("utf-8", "replace")
    except Exception as erro:  # noqa: BLE001
        raise ErroDeConexao(f"resposta de autorização ilegível: {resposta[:120]}") from erro

    campos = _parse_kv(decodificado)
    if campos.get("ftp_msg"):
        raise ErroDeConexao(f"o servidor recusou a conexão: {campos['ftp_msg']}")
    if not campos.get("host"):
        raise ErroDeConexao(f"autorização sem host: {sorted(campos)}")

    return Conexao(
        host=campos["host"],
        root=campos.get("root", ""),
        port=int(campos.get("port") or 0),
        username=campos.get("username", ""),
        password=campos.get("password", ""),
    )


def _url_http(conexao: Conexao, caminho: str) -> str:
    # Os nomes têm espaço, vírgula, apóstrofo e acento — cada segmento precisa ser escapado.
    partes = [urllib.parse.quote(p, safe="") for p in caminho.split("/")]
    return f"{conexao.base_url}/" + "/".join(partes)


ERROS_DE_REDE = (urllib.error.URLError, socket.timeout, OSError, *ftplib.all_errors)


class Sessao:
    """Baixa arquivos reusando uma única conexão.

    Reabrir o FTP a cada arquivo custaria um login por arquivo — em 4.756 arquivos, mais de uma
    hora só de handshake. A conexão é mantida aberta e reaberta apenas quando cai.
    """

    def __init__(self, conexao: Conexao | None = None):
        self.conexao = conexao or obter_conexao()
        self._ftp: ftplib.FTP | None = None

    def __enter__(self) -> "Sessao":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    def fechar(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.quit()
            except Exception:  # noqa: BLE001
                self._ftp.close()
            self._ftp = None

    def _ftp_ativo(self) -> ftplib.FTP:
        if self._ftp is None:
            ftp = ftplib.FTP(timeout=TIMEOUT)
            ftp.connect(self.conexao.host_puro.split(":")[0], self.conexao.port or 21)
            ftp.login(self.conexao.username, self.conexao.password)
            ftp.set_pasv(True)
            self._ftp = ftp
        return self._ftp

    def _baixar_ftp(self, caminho: str, parcial: Path, ja_baixado: int) -> None:
        ftp = self._ftp_ativo()
        remoto = f"{self.conexao.root_normalizado}/{caminho}".lstrip("/")
        with parcial.open("ab" if ja_baixado else "wb") as saida:
            ftp.retrbinary(
                f"RETR {remoto}", saida.write, blocksize=256 * 1024, rest=ja_baixado or None
            )

    def _baixar_http(self, caminho: str, parcial: Path, ja_baixado: int) -> None:
        req = urllib.request.Request(
            _url_http(self.conexao, caminho), headers={"User-Agent": USER_AGENT}
        )
        if ja_baixado:
            req.add_header("Range", f"bytes={ja_baixado}-")

        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            # Se pedimos Range e veio 200, o servidor ignorou o pedido e está mandando o arquivo
            # inteiro — reescrever do zero, porque concatenar corromperia o arquivo.
            retomando = ja_baixado > 0 and resp.status == 206
            with parcial.open("ab" if retomando else "wb") as saida:
                while bloco := resp.read(256 * 1024):
                    saida.write(bloco)

    def baixar(
        self,
        caminho: str,
        destino: Path,
        tamanho_esperado: int | None = None,
        tentativas: int = 4,
    ) -> int:
        """Baixa `caminho` (relativo à raiz do servidor) para `destino`, retomando o que já veio.

        Escreve num `.part` e só promove ao destino final quando o tamanho confere — uma queda no
        meio nunca deixa para trás um arquivo truncado se passando por completo.
        """
        destino.parent.mkdir(parents=True, exist_ok=True)
        parcial = destino.with_suffix(destino.suffix + ".part")

        for tentativa in range(1, tentativas + 1):
            ja_baixado = parcial.stat().st_size if parcial.exists() else 0
            try:
                if self.conexao.is_ftp:
                    self._baixar_ftp(caminho, parcial, ja_baixado)
                else:
                    self._baixar_http(caminho, parcial, ja_baixado)
                break
            except ERROS_DE_REDE as erro:
                self.fechar()  # a conexão pode ter morrido; a próxima tentativa reabre
                if tentativa == tentativas:
                    raise ErroDeConexao(f"falha ao baixar {caminho}: {erro}") from erro
                time.sleep(2**tentativa)

        tamanho = parcial.stat().st_size
        # Piso, não igualdade: menor que o esperado é download truncado; maior é o servidor tendo
        # trocado o arquivo por uma versão melhor sem atualizar o `size` do catálogo.
        if tamanho_esperado is not None and tamanho < tamanho_esperado:
            raise ErroDeConexao(
                f"{caminho}: baixou só {tamanho} de {tamanho_esperado} bytes (truncado)"
            )

        parcial.replace(destino)
        return tamanho


def baixar(
    conexao: Conexao,
    caminho: str,
    destino: Path,
    tamanho_esperado: int | None = None,
) -> int:
    """Baixa um arquivo avulso (abre e fecha a conexão)."""
    with Sessao(conexao) as sessao:
        return sessao.baixar(caminho, destino, tamanho_esperado)
