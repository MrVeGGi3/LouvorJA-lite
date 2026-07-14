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
./scripts/build_appimage.sh                # dist/LouvorJA-Lite-x86_64.AppImage (~21 MB)
python scripts/build_pacote.py --baixar    # AppImage + data/ prontos para o pendrive
```

O AppImage **não** contém as músicas — os ~15 GB ficam na pasta `data/` ao lado dele. O app
procura os dados nesta ordem:

1. `LOUVORJA_LITE_DATA_DIR`, se definida;
2. `data/` ao lado do `.AppImage` (o caso do pendrive);
3. `~/.local/share/louvorja-lite`.

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
