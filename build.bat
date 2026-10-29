@echo off
chcp 65001 >nul
rem AKICHEAST 3D: Tests ausführen und Windows-.exe bauen
rem Ergebnis: dist\AKICHEAST3D\AKICHEAST3D.exe
setlocal
cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Virtuelle Umgebung fehlt. Bitte zuerst einrichten:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    exit /b 1
)

echo Tests laufen ...
"%PYTHON%" -m pytest -q
if errorlevel 1 (
    echo Tests fehlgeschlagen, die .exe wird nicht gebaut.
    exit /b 1
)

echo Baue .exe ...
"%PYTHON%" -m PyInstaller --noconfirm --clean --windowed ^
    --name AKICHEAST3D ^
    --paths "%~dp0src" ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build" ^
    --specpath "%~dp0build" ^
    "%~dp0src\akicheast3d\main.py"
if errorlevel 1 (
    echo Build fehlgeschlagen.
    exit /b 1
)

echo Fertig: dist\AKICHEAST3D\AKICHEAST3D.exe
