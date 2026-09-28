# LouvorJA Lite

Versão simplificada do [LouvorJA Desktop](https://github.com/louvorja/desktop) — busca de hinos,
montagem de liturgia semanal, player de áudio (cantado e playback) e um modo de exibição em tela
cheia para projeção, com a virada de slide sincronizada com a música. Web app local
(FastAPI + HTML/JS vanilla), sem build step e sem dependências de CDN.

Distribuível como um **AppImage** que roda direto do pendrive, com todas as músicas junto — sem
precisar de internet na igreja.

O AppImage **basta por si só**: aberto numa máquina zerada, ele pergunta onde guardar os dados e
baixa o catálogo e as músicas pela própria tela, sem terminal e sem Python instalado. A pasta
`data/` pronta continua sendo o caminho mais rápido (nada a baixar na hora), mas deixou de ser
obrigatória.

## Baixando os hinos pela interface

O botão **"⤓ Músicas"**, no topo da tela de controle, abre o download:

- **Baixar catálogo de hinos** — traz o `database.db` (~90 MB). É o primeiro passo numa instalação
  nova; sem ele não há o que buscar nem projetar.
- **Baixar tudo** — o catálogo inteiro de mídia (4.756 arquivos, ~14 GB).
- **Por álbum** — são 75, cada um mostrando quanto já está em disco (`430/1965 · faltam 2,4 GB`) e
  baixando sozinho. O Hinário Adventista (1.965 arquivos, 3,2 GB) fica fixado no topo.
- **Baixar agora**, no player — quando um hino selecionado está sem o mp3, o aviso vira um botão
  que puxa só aquele arquivo, em segundos.

Um download por vez, com barra de progresso, velocidade e tempo restante. Dá para **parar** e
retomar depois: um arquivo interrompido continua do byte exato onde parou, e o que já está íntegro
em disco nunca é rebaixado. Na primeira execução o app pergunta onde guardar tudo — ao lado do
programa (modo pendrive, leva os hinos de um computador para outro) ou na pasta pessoal.

## Início rápido

Do zero até projetando, numa máquina com internet — um comando só monta o ambiente, obtém o banco,
baixa a mídia (~15 GB) e sobe o servidor:

```bash
./scripts/setup.sh --tudo
```

Tudo é idempotente: se algo cair no meio (o download é retomável), rode de novo que ele continua de
onde parou. Dá para separar as etapas quando for conveniente:

```bash
./scripts/setup.sh          # 1. cria o .venv e instala as dependências
./scripts/setup.sh --dados  # 2. obtém o banco de hinos e baixa a mídia
./scripts/setup.sh --run    # 3. sobe o servidor em http://127.0.0.1:8000
```

Depois, abra `http://127.0.0.1:8000/controle` na tela do operador. Ao selecionar um hino e clicar
em "Abrir Projeção", uma nova janela abre em `http://127.0.0.1:8000/projecao` — arraste para o
segundo monitor/telão e pressione F11.

Atalhos (valem nas **duas** janelas, controle e projeção): `→`/espaço próximo slide, `←`
anterior, `B` escurece a tela sem perder o hino. Só na projeção: `PgDn`/`PgUp` (o que os controles
remotos de apresentação mandam), `F` entra/sai de tela cheia. Só no controle: `P` toca/pausa.

## De onde vêm os dados

O passo 2 (`--dados`) chama o `scripts/sync_data.py`, que **encontra o banco de hinos
(`database.db`) sozinho**, nesta ordem:

1. um LouvorJA Desktop instalado (`~/.local/share/LouvorJA/config`), que **pode** já trazer
   capas/imagens — mas um Desktop que nunca baixou mídia guarda ali só o `database.db`, e aí as
   imagens vêm do servidor como qualquer outra mídia (veja abaixo);
2. o `data/database.db` já presente (`data/` copiado de outra máquina — não reimporta);
3. senão, baixa `config/pt_database.db` do servidor oficial — funciona numa máquina zerada.

Em seguida ele baixa a mídia (áudios e imagens) do mesmo servidor oficial que o app original usa.

A lógica de download mora em `app/sync/` — é de lá que a tela do app a usa, e é por isso que ela
entra no bundle do AppImage. Os scripts abaixo são a porta de linha de comando para o mesmo código,
úteis para preparar um pendrive em lote. Para rodar essas etapas na mão, sem o `setup.sh`:

```bash
# o banco (encontra a origem sozinho; use as flags só para forçar):
python scripts/sync_data.py                      # automático (Desktop > data/ > servidor)
python scripts/sync_data.py --do-servidor        # força baixar do servidor
python scripts/sync_data.py --source /caminho/config   # força uma pasta config/ do Desktop

# a mídia:
python scripts/download_media.py --dry-run       # quanto pesa (4.756 arquivos, ~15 GB)
python scripts/download_media.py --only image    # só os fundos dos slides (1.265 arquivos, 0,4 GB)
python scripts/download_media.py --album 712     # só o Hinário Adventista
python scripts/download_media.py                 # o catálogo inteiro
```

O `--only image` merece atenção porque é barato e muda a cara da projeção: sem as imagens o slide
cai no fundo preto com a letra por cima (o comportamento de reserva, não um defeito), e são só
0,4 GB dos ~15 GB do catálogo. O "Baixar agora" do player traz **apenas o mp3** do hino
selecionado — se os fundos não aparecem mesmo com a música tocando, é esse o passo que falta.

O download é idempotente e retomável: se cair no meio, é só rodar de novo — ele continua de onde
parou, inclusive no meio de um arquivo. O layout em disco (`data/musicas/<Álbum>/<Nome>.mp3`)
espelha o do LouvorJA Desktop, então também dá para semear a pasta `data/` copiando de outra
máquina em vez de baixar tudo.

## Sem o setup.sh (passos manuais)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/sync_data.py            # encontra o banco sozinho
python scripts/download_media.py       # baixa a mídia (~15 GB)
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Player e sincronia

A barra de baixo tem dois modos, e a escolha fica guardada no navegador — vale para os hinos
seguintes e para a próxima vez que o app abrir:

- **♪ Seguir áudio** — o áudio toca na janela de **controle** (a de projeção nunca recebe um gesto
  do usuário, e o navegador bloquearia o autoplay lá) e o slide vira sozinho no tempo gravado no
  banco (`lyrics.time` para o cantado, `instrumental_time` para o playback). Arrastar a barra de
  progresso reposiciona a projeção junto.
- **Só slides** — para o louvor ao vivo, com a banda ou a congregação cantando: projetar um hino
  não toca nada, e a virada é toda na mão. O player continua na tela, então dá para dar ▶ no meio
  se precisar do som mesmo assim.

Trocar de modo no meio do hino não assusta: entrar em "Só slides" cala a música onde ela está, e
voltar para "Seguir áudio" não sai tocando sozinho — o ▶ é que retoma.

Músicas sem áudio baixado continuam projetando normalmente; só o player fica escondido.

## Gerando o pacote pro pendrive

Um comando monta tudo — instala as dependências de build, baixa a mídia que faltar e empacota:

```bash
./scripts/setup.sh --pacote
```

O resultado fica em `dist/LouvorJA-Lite-<versão>/` (AppImage + `data/` + `LEIAME.txt`) — é essa
pasta que vai inteira para o pendrive. Os passos individuais, se preferir rodá-los à mão:

```bash
./scripts/build_appimage.sh                # só o dist/LouvorJA-Lite-x86_64.AppImage (~21 MB)
python scripts/build_pacote.py --baixar    # empacota o AppImage + data/ (baixando o que faltar)
```

O `build_appimage.sh` usa PyInstaller, que fica no grupo opcional `build` do `pyproject.toml`
(instale com `pip install -e ".[build]"`, ou deixe o `setup.sh --pacote` cuidar disso).

O AppImage **não** contém as músicas — os ~15 GB ficam na pasta `data/` ao lado dele (o AppImage
cru, sem dados, é o `dist/LouvorJA-Lite-x86_64.AppImage`). Em execução, o app procura os dados
nesta ordem:

1. `LOUVORJA_LITE_DATA_DIR`, se definida;
2. a pasta escolhida na primeira execução, gravada em `~/.config/louvorja-lite/config.json`;
3. `data/` ao lado do `.AppImage` (o caso do pendrive);
4. `~/.local/share/louvorja-lite`.

Rodando do código-fonte o passo 2 é ignorado e `data/` do repositório vale — assim um teste do
AppImage não sequestra o ambiente de desenvolvimento.

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
  apontando para ela), o app abre na tela de download em vez de encontrar os hinos — o que resolve
  com internet, mas não no meio do culto.

## Instalando um novo release

1. Baixe o `LouvorJA-Lite-x86_64.AppImage` da [página de releases](https://github.com/MrVeGGi3/LouvorJA-lite/releases)
   e substitua o antigo **no mesmo lugar** (ao lado da pasta `data/`, no caso do pendrive). Os
   hinos, as liturgias e os momentos fixos ficam no `data/` e não precisam ser baixados de novo.
2. Feche o app antigo antes de abrir o novo — senão o novo sobe na porta seguinte (8001, 8002…) e
   a janela de projeção que estava no telão continua apontando para a versão velha.
3. Na tela de controle, aperte **Ctrl+Shift+R** uma vez, e o mesmo na janela de projeção.

O passo 3 é o que mais engana: o app novo abre no mesmo endereço do antigo
(`http://127.0.0.1:8000`), e o navegador pode reaproveitar por alguns dias o HTML/JS/CSS que já
tinha guardado da versão anterior. O sintoma é a tela sem as novidades do release — por exemplo, a
0.3.0 aparecendo sem o seletor "♪ Seguir áudio | Só slides". O Ctrl+Shift+R recarrega ignorando
essa cópia guardada.

Use de preferência **Google Chrome ou Chromium**: o app abre neles quando estão instalados, e só
eles colocam a projeção sozinha no telão (ver [Limitações conhecidas](#limitações-conhecidas)). No
Firefox tudo funciona, mas botões e campos têm outra cara e a projeção precisa ser arrastada até o
telão. Para instalar o Chrome no Ubuntu/Pop!_OS:

```bash
wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install /tmp/chrome.deb
```

## Testes

```bash
pytest

# confere as queries contra um banco real, não contra a fixture:
LOUVORJA_REAL_DB=~/.local/share/LouvorJA/config/database.db pytest tests/test_schema_contract.py
```

## Limitações conhecidas

- Com a tela **estendida** a janela de projeção vai sozinha para o telão (Window Management API,
  só no Chromium e com a permissão concedida); fora disso — outro navegador, permissão negada ou
  tela **espelhada**, onde não há para onde mover — ela nasce como janela normal, e é o `F`/duplo
  clique que a põe em tela cheia. Espelhado, a projeção cobre o controle e fica com o foco do
  teclado: é para isso que as teclas de virar slide funcionam também na janela de projeção.
- Liturgias antigas (`liturgia.ja` do LouvorJA Desktop) não são migradas — o formato aqui é novo
  (JSON), começando do zero.
- O banco não guarda mais cor nem tamanho de letra. A projeção reproduz o estilo do LouvorJA
  Desktop: Arial Narrow negrito branca, centralizada, com o tamanho da fonte em 14% da altura da
  tela (10% para a letra auxiliar) — os mesmos defaults do original. Para mudar, ajuste
  `--tamanho-letra` em `app/static/projecao.css`. A fonte vai embutida em `app/static/fontes/`
  (Liberation Sans Narrow, clone métrico da Arial Narrow), para o pacote projetar igual num PC
  que não a tenha instalada.
- O catálogo em espanhol existe no banco, mas não é baixado nem exibido.
