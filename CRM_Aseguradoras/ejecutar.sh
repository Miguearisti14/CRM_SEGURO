#!/bin/bash

# Arranca el servidor Django en macOS/Linux.
# Uso: ./ejecutar.sh

set -euo pipefail

DIR="$(cd -- "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "========================================"
echo "  SURA CRM - INICIANDO"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python3 no instalado"
    echo "Instala Python desde: https://www.python.org/downloads/"
    echo "O con Homebrew: brew install python3"
    exit 1
fi

echo "[OK] Python3 detectado"
python3 --version

# Verificar manage.py
if [ ! -f "manage.py" ]; then
    echo "[ERROR] No encuentro manage.py. Ejecuta este script desde la carpeta del proyecto."
    exit 1
fi

# Activar venv si existe
if [ -d ".venv" ]; then
    echo "Activando entorno .venv"
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Abrir navegador tras 3 segundos (macOS: open; Linux: xdg-open)
(
    sleep 3
    if command -v open >/dev/null 2>&1; then
        open "http://127.0.0.1:8000"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
    fi
) &

echo "[*] Servidor en: http://127.0.0.1:8000"
echo "[*] Para detener: Ctrl+C"
echo "========================================"
echo ""

# Iniciar servidor Django
python3 manage.py runserver 127.0.0.1:8000
