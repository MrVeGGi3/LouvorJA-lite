# LouvorJA Lite

Versão simplificada do [LouvorJA Desktop](https://github.com/louvorja/desktop) — busca de
hinos, montagem de liturgia semanal e um modo de exibição em tela cheia para projeção. Sem
player de áudio, sem sincronização com o servidor oficial, sem as demais telas do app
original. Web app local (FastAPI + HTML/JS vanilla), sem build step e sem dependências de CDN.

## Origem dos dados

Este projeto **não baixa dados de nenhum servidor** — ele lê o `database.db` (SQLite) e as
imagens (`capas/`, `imagens/`) já baixados por uma instalação existente do LouvorJA Desktop,
normalmente em `~/.local/share/LouvorJA/config/`.

```bash
python scripts/sync_data.py                     # usa o caminho padrão acima
python scripts/sync_data.py --source /outro/caminho/config
```

O comando é idempotente — pode ser reexecutado a qualquer momento para atualizar `data/`
(banco + imagens) sem afetar as liturgias já criadas em `data/liturgias/`. Por padrão só copia
imagens efetivamente referenciadas pelo banco (`--images referenced`); use `--images full` para
copiar as pastas inteiras, `--images symlink` para não duplicar espaço em disco (mesma
máquina), ou `--images none` para pular imagens.

## Rodando

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/sync_data.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/controle` na tela do operador. Ao selecionar um hino e clicar em
"Abrir Projeção", uma nova janela abre em `http://127.0.0.1:8000/projecao` — arraste para o
segundo monitor/telão e pressione F11 para tela cheia.

## Testes

```bash
pytest
```

## Limitações conhecidas (aceitas no MVP)

- Tamanho de letra é aplicado em `pt` diretamente do valor gravado no banco — não se
  auto-ajusta à resolução do telão.
- Nenhuma detecção automática de monitor — a janela de projeção precisa ser arrastada
  manualmente para a tela correta.
- Liturgias antigas (`liturgia.ja` do LouvorJA Desktop) não são migradas — o formato de
  liturgia aqui é novo (JSON), começando do zero.
- O vínculo entre um hino do hinário (`HINARIO_ADVENTISTA`) e sua letra/slides
  (`MUSICAS_SLIDE`/`MUSICAS_LETRA`) é resolvido por nome (`NOME_COM`), já que os espaços de ID
  dessas tabelas não coincidem. Vale revalidar essa heurística contra um banco real na primeira
  sincronização.
