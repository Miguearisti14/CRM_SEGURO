#!/bin/bash

echo "========================================"
echo "  INSTALADOR SURA CRM v1.0"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no instalado"
    echo ""
    echo "Instala Python desde: https://www.python.org/downloads/"
    echo "O con Homebrew: brew install python3"
    echo ""
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo "[OK] Python3 detectado"
python3 --version

# Verificar requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "[ERROR] requirements.txt no encontrado"
    exit 1
fi

echo ""
echo "Instalando dependencias..."
echo "(Esto tomará 1-2 minutos)"
echo ""

python3 -m pip install --upgrade pip --user --quiet
python3 -m pip install -r requirements.txt --user --quiet

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] No se pudieron instalar dependencias"
    echo "Intentando sin modo silencioso..."
    python3 -m pip install -r requirements.txt --user
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi

echo ""
echo "[OK] Dependencias instaladas"

# Verificar base de datos
if [ ! -f "db.sqlite3" ]; then
    echo ""
    echo "Creando base de datos..."
    python3 manage.py migrate --noinput
fi

echo ""
echo "========================================"
echo "  INSTALACION COMPLETADA"
echo "========================================"
echo ""
echo "Para ejecutar: ./ejecutar.sh"
echo ""

read -p "Presiona Enter para continuar..."