# LouvorJA Lite

Versão simplificada do [LouvorJA Desktop](https://github.com/louvorja/desktop) — busca de hinos,
montagem de liturgia semanal, player de áudio (cantado e playback) e um modo de exibição em tela
cheia para projeção, com a virada de slide sincronizada com a música. Web app local
(FastAPI + HTML/JS vanilla), sem build step e sem dependências de CDN.

Distribuível como um **AppImage** que roda direto do pendrive, com todas as músicas junto — sem
precisar de internet na igreja.

## Origem dos dados

O banco de hinos (`database.db`) vem de uma instalação existente do LouvorJA Desktop, normalmente
em `~/.local/share/LouvorJA/config/`:

```bash
python scripts/sync_data.py                     # usa o caminho padrão acima
python scripts/sync_data.py --source /outro/caminho/config
```

Os áudios e imagens são baixados do servidor oficial do LouvorJA — o mesmo que o app original usa:

```bash
python scripts/download_media.py --dry-run      # quanto pesa (4.756 arquivos, ~15 GB)
python scripts/download_media.py --album 712    # só o Hinário Adventista
python scripts/download_media.py                # o catálogo inteiro
```

O download é idempotente e retomável: se cair no meio, é só rodar de novo — ele continua de onde
parou, inclusive no meio de um arquivo. O layout em disco (`data/musicas/<Álbum>/<Nome>.mp3`)
espelha o do LouvorJA Desktop, então também dá para semear a pasta `data/` copiando de outra
máquina em vez de baixar tudo.

## Rodando

O `scripts/setup.sh` cria o `.venv` (se ainda não existir), instala as dependências e — com as
flags — importa o banco, baixa a mídia e monta o pacote. É idempotente: rodar de novo continua de
onde parou.

```bash
./scripts/setup.sh          # cria .venv + instala as dependências
./scripts/setup.sh --run    # e já sobe o servidor em http://127.0.0.1:8000
./scripts/setup.sh --dados  # importa o banco (sync_data) e baixa a mídia (~15 GB)
./scripts/setup.sh --pacote # monta dist/LouvorJA-Lite-<versão>/ (AppImage + data/) pro pendrive
```

Passe `--source /caminho/config` para importar o banco de outra instalação do LouvorJA Desktop. À
mão, os mesmos passos são:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/sync_data.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/controle` na tela do operador. Ao selecionar um hino e clicar em
"Abrir Projeção", uma nova janela abre em `http://127.0.0.1:8000/projecao` — arraste para o
segundo monitor/telão e pressione F11.

Atalhos: `→`/espaço próximo slide, `←` anterior, `P` toca/pausa.

### Player e sincronia

O áudio toca na janela de **controle** (a de projeção nunca recebe um gesto do usuário, e o
navegador bloquearia o autoplay lá). Com "Seguir áudio" ligado, o slide vira sozinho no tempo
gravado no banco (`lyrics.time` para o cantado, `instrumental_time` para o playback) — arrastar a
barra de progresso reposiciona a projeção junto. Desligue a opção para navegar na mão.

Músicas sem áudio baixado continuam projetando normalmente; só o player fica escondido.

## Gerando o executável

```bash
./scripts/setup.sh --pacote                # tudo de uma vez: deps de build + mídia + pacote
./scripts/build_appimage.sh                # só o dist/LouvorJA-Lite-x86_64.AppImage (~21 MB)
python scripts/build_pacote.py --baixar    # AppImage + data/ prontos para o pendrive
```

O `build_appimage.sh` usa PyInstaller, que fica no grupo opcional `build` do `pyproject.toml`
(instale com `pip install -e ".[build]"`, ou deixe o `setup.sh --pacote` cuidar disso).

O AppImage **não** contém as músicas — os ~15 GB ficam na pasta `data/` ao lado dele. O app
procura os dados nesta ordem:

1. `LOUVORJA_LITE_DATA_DIR`, se definida;
2. `data/` ao lado do `.AppImage` (o caso do pendrive);
3. `~/.local/share/louvorja-lite`.

O `build_pacote.py` deixa tudo pronto em `dist/LouvorJA-Lite-<versão>/` (AppImage + `data/` +
`LEIAME.txt`) — é essa pasta que vai inteira para o pendrive. O AppImage cru, sem os dados ao lado,
fica em `dist/LouvorJA-Lite-x86_64.AppImage`.

## Testando o pendrive em outro computador

Formate o pendrive em **exFAT** (FAT32 funciona — nenhum arquivo passa de 4 GB —, mas copiar os
~15 GB nele é bem mais lento). Copie a pasta `dist/LouvorJA-Lite-<versão>/` inteira, mantendo o
AppImage e o `data/` **juntos**.

No outro computador (precisa ser **Linux x86_64** — não roda em Windows, Mac nem ARM):

```bash
cd /run/media/USUARIO/LouvorJA-Lite
./LouvorJA-Lite-x86_64.AppImage
# se der erro, use o fallback que extrai e roda sem FUSE:
./LouvorJA-Lite-x86_64.AppImage --appimage-extract-and-run
```

Os três tropeços mais comuns:

- **O bit de executável some no exFAT/FAT.** Esses sistemas de arquivo não guardam a permissão de
  execução, então rodar direto do pendrive pode falhar mesmo depois do `chmod +x`. Use
  `--appimage-extract-and-run` ou copie a pasta para o disco do PC antes de rodar.
- **Falta a `libfuse2`.** O AppImage precisa de FUSE; em distros novas (Ubuntu 22.04+) costuma
  faltar e dá um erro tipo `dlopen: libfuse.so.2`. Na hora, `--appimage-extract-and-run` resolve;
  de forma definitiva, `sudo apt install libfuse2` no computador de destino.
- **Separar o `data/` do AppImage.** Sem a pasta `data/` ao lado (ou uma `LOUVORJA_LITE_DATA_DIR`
  apontando para ela), o app não acha o banco de hinos nem os áudios.

## Testes

```bash
pytest

# confere as queries contra um banco real, não contra a fixture:
LOUVORJA_REAL_DB=~/.local/share/LouvorJA/config/database.db pytest tests/test_schema_contract.py
```

## Limitações conhecidas

- Nenhuma detecção automática de monitor — a janela de projeção precisa ser arrastada
  manualmente para a tela correta.
- Liturgias antigas (`liturgia.ja` do LouvorJA Desktop) não são migradas — o formato aqui é novo
  (JSON), começando do zero.
- O banco não guarda mais cor nem tamanho de letra. A projeção reproduz o estilo do LouvorJA
  Desktop: Arial Narrow negrito branca, centralizada, com o tamanho da fonte em 14% da altura da
  tela (10% para a letra auxiliar) — os mesmos defaults do original. Para mudar, ajuste
  `--tamanho-letra` em `app/static/projecao.css`. A fonte vai embutida em `app/static/fontes/`
  (Liberation Sans Narrow, clone métrico da Arial Narrow), para o pacote projetar igual num PC
  que não a tenha instalada.
- O catálogo em espanhol existe no banco, mas não é baixado nem exibido.
