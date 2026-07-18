@echo off
chcp 65001 > nul
setlocal
title Magik Shoes BI - Lanzador

echo ======================================================
echo          INICIANDO ECOSISTEMA MAGIK SHOES BI
echo ======================================================
echo.

:: Configuración de rutas
set PYTHON_EXE=%~dp0.venv\Scripts\python.exe
set SCRIPTS_DIR=%~dp0scripts

:: Proceso ETL
echo [PASO 1/4] Iniciando proceso ETL...
"%PYTHON_EXE%" "%SCRIPTS_DIR%\etl_script.py"

:: Si hay error entonces ejecutar el último paso
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ADVERTENCIA] No se pudo realizar el proceso ETL.
    timeout /t 5
    goto LANZAR_APP
)

:: Predicciones
echo.
echo [PASO 2/4] Entrenando modelos y generando proyecciones...
"%PYTHON_EXE%" "%SCRIPTS_DIR%\predict_manager_day.py"
"%PYTHON_EXE%" "%SCRIPTS_DIR%\predict_manager_month.py"
"%PYTHON_EXE%" "%SCRIPTS_DIR%\predict_inventory.py"

:LANZAR_APP
:: Aplicación
echo.
echo [PASO 3/4] Lanzando Aplicación Panel de Control y Asistente IA...
echo Por favor, no cierre esta ventana mientras use la app.
echo.
"%PYTHON_EXE%" "%~dp0run_app.py"

echo.
echo Proceso de arranque completado.
pause