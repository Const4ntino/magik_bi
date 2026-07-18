@echo off
chcp 65001 > nul
title Instalador Magik Shoes BI
color 0A

echo ======================================================
echo      CONFIGURANDO ENTORNO - MAGIK SHOES
echo ======================================================

:: 1. Creacin del entorno virtual
echo [1/3] Creando entorno virtual (.venv)...
python -m venv .venv

:: 2. Activacion e instalacion de dependencias
echo [2/3] Instalando librerías (puede tardar unos minutos)...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Entorno configurado correctamente.
echo.
echo Ya puede cerrar esta ventana.
pause