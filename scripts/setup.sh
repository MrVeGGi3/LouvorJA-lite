#!/usr/bin/env bash
# Bootstrap do LouvorJA Lite: cria o .venv (se preciso), instala as dependências e,
# opcionalmente, importa/baixa os dados e monta o pacote pro pendrive.
#
# Tudo aqui é idempotente — rodar de novo continua de onde parou, não refaz o que já existe.
#
#   ./scripts/setup.sh                  # cria .venv + instala as deps
#   ./scripts/setup.sh --dados          # + importa o banco e baixa a mídia (~15 GB)
#   ./scripts/setup.sh --pacote         # + monta dist/LouvorJA-Lite-<versão>/ (AppImage + data/)
#   ./scripts/setup.sh --run            # + sobe o servidor em http://127.0.0.1:8000
#   ./scripts/setup.sh --source /caminho/config   # banco de outra instalação do LouvorJA Desktop
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$RAIZ/.venv"
PY="$VENV/bin/python"

DADOS=0 PACOTE=0 RUN=0
SOURCE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dados)  DADOS=1 ;;
    --pacote) PACOTE=1 ;;
    --run)    RUN=1 ;;
    --source) SOURCE="${2:?--source precisa de um caminho}"; shift ;;
    -h|--help)
      sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
  shift
done

# O --pacote precisa do PyInstaller (grupo build) para gerar o AppImage.
EXTRAS="dev"
[[ $PACOTE -eq 1 ]] && EXTRAS="dev,build"

if [[ ! -d "$VENV" ]]; then
  echo "==> Criando o virtualenv em .venv"
  python3 -m venv "$VENV"
fi

echo "==> Instalando dependências (.[$EXTRAS])"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -e "$RAIZ[$EXTRAS]"

if [[ $DADOS -eq 1 || $PACOTE -eq 1 ]]; then
  echo "==> Importando o banco do LouvorJA Desktop"
  if [[ -n "$SOURCE" ]]; then
    "$PY" "$RAIZ/scripts/sync_data.py" --source "$SOURCE"
  else
    "$PY" "$RAIZ/scripts/sync_data.py"
  fi
fi

if [[ $PACOTE -eq 1 ]]; then
  # build_pacote.py --baixar baixa a mídia que faltar e roda o build_appimage.sh.
  echo "==> Montando o pacote (baixa a mídia que faltar + AppImage)"
  "$PY" "$RAIZ/scripts/build_pacote.py" --baixar
elif [[ $DADOS -eq 1 ]]; then
  echo "==> Baixando a mídia (~15 GB, retomável)"
  "$PY" "$RAIZ/scripts/download_media.py"
fi

echo "==> Pronto. Ative o ambiente com: source .venv/bin/activate"

if [[ $RUN -eq 1 ]]; then
  echo "==> Subindo o servidor em http://127.0.0.1:8000/controle"
  exec "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000
fi
