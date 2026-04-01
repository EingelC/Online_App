@echo off
title Instalador de Dependencias - App
color 0A

echo =====================================================
echo    CONFIGURANDO ENTORNO PARA APP
echo =====================================================
echo.

:: 1. Verificar si Python existe. Si no, descargarlo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python no detectado. Descargando instalador...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe -OutFile python_installer.exe"
    
    echo [!] Instalando Python... Por favor espera.
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    :: Forzar actualizacion del PATH en esta sesion
    set "PATH=%PATH%;%ProgramFiles%\Python312\;%ProgramFiles%\Python312\Scripts\"
    del python_installer.exe
    echo [OK] Python instalado.
) else (
    echo [OK] Python ya esta presente.
)

:: 2. Actualizar PIP
echo.
echo [+] Actualizando PIP...
python -m pip install --upgrade pip

:: 3. Instalar librerias una por una
echo.
echo [+] Instalando librerias necesarias...
echo Esto requiere internet.
echo.

python -m pip install customtkinter --quiet
echo --- customtkinter instalado
python -m pip install firebase-admin --quiet
echo --- firebase-admin instalado
python -m pip install gspread --quiet
echo --- gspread instalado
python -m pip install google-auth --quiet
echo --- google-auth instalado
python -m pip install cryptography --quiet
echo --- cryptography instalado
python -m pip install pandas --quiet
echo --- pandas instalado

echo.
echo =====================================================
echo    PROCESO TERMINADO
echo =====================================================
pause