@echo off
chcp 65001 > nul
setlocal
title Magik Shoes BI - app

:: Configuración de rutas
set PYTHON_EXE=%~dp0.venv\Scripts\python.exe

:: Lanzar aplicación
echo Lanzando Aplicación Panel de Control y Asistente IA...
echo Por favor, no cierre esta ventana mientras use la app.
echo.
"%PYTHON_EXE%" "%~dp0run_app.py"

echo.
echo Proceso de arranque completado.
pause