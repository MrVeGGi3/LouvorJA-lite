#!/usr/bin/env bash
# Gera o LouvorJA-Lite-x86_64.AppImage a partir do bundle do PyInstaller.
#
# A pasta data/ (banco + músicas) NÃO entra no AppImage — ela fica ao lado dele. Veja
# scripts/build_pacote.py, que monta o pacote completo para pendrive.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$RAIZ/build"
APPDIR="$BUILD/AppDir"
DIST="$RAIZ/dist"
PY="${PY:-$RAIZ/.venv/bin/python}"
ARQ="${ARCH:-x86_64}"

echo "==> PyInstaller"
"$PY" -m PyInstaller --noconfirm \
  --distpath "$BUILD/dist" --workpath "$BUILD/work" \
  "$RAIZ/scripts/louvorja-lite.spec"

echo "==> Montando o AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$BUILD/dist/louvorja-lite/." "$APPDIR/usr/bin/"
cp "$RAIZ/assets/louvorja-lite.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/louvorja-lite.png"
cp "$RAIZ/assets/louvorja-lite.png" "$APPDIR/louvorja-lite.png"

cat > "$APPDIR/louvorja-lite.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=LouvorJA Lite
Comment=Projeção de hinos com player de áudio
Exec=louvorja-lite
Icon=louvorja-lite
Categories=AudioVideo;Audio;Player;
Terminal=true
EOF
cp "$APPDIR/louvorja-lite.desktop" "$APPDIR/usr/share/applications_desktop" 2>/dev/null || true

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
# $APPIMAGE aponta para o .AppImage de verdade (no pendrive); $APPDIR é o mount somente-leitura.
AQUI="$(dirname "$(readlink -f "${APPIMAGE:-$0}")")"

if [ ! -f "${LOUVORJA_LITE_DATA_DIR:-$AQUI/data}/database.db" ] && [ ! -f "$HOME/.local/share/louvorja-lite/database.db" ]; then
  echo "LouvorJA Lite: não achei os dados." >&2
  echo "Esperava a pasta 'data/' (com database.db) ao lado do AppImage, em:" >&2
  echo "  $AQUI/data" >&2
  echo "Ou aponte LOUVORJA_LITE_DATA_DIR para onde ela estiver." >&2
  exit 1
fi

exec "$(dirname "$(readlink -f "$0")")/usr/bin/louvorja-lite" "$@"
EOF
chmod +x "$APPDIR/AppRun"

echo "==> appimagetool"
FERRAMENTA="$BUILD/appimagetool-$ARQ.AppImage"
if [ ! -x "$FERRAMENTA" ]; then
  URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARQ.AppImage"
  echo "    baixando de $URL"
  curl -fsSL -o "$FERRAMENTA" "$URL" || {
    echo "ERRO: não consegui baixar o appimagetool. Baixe manualmente para $FERRAMENTA" >&2
    exit 1
  }
  chmod +x "$FERRAMENTA"
fi

mkdir -p "$DIST"
SAIDA="$DIST/LouvorJA-Lite-$ARQ.AppImage"

# --appimage-extract-and-run: o appimagetool é ele próprio um AppImage e precisa de FUSE, que
# nem sempre existe (container, live-USB). Extrair evita depender disso.
ARCH="$ARQ" "$FERRAMENTA" --appimage-extract-and-run "$APPDIR" "$SAIDA"

echo
echo "OK -> $SAIDA"
ls -lh "$SAIDA"
