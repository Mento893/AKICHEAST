@echo off
chcp 65001 >nul
rem AKICHEAST 3D: Tests ausführen, Windows-.exe bauen und mit einem Selbsttest prüfen
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
rem pylibjpeg findet seine Dekoder über Paket-Metadaten, die müssen mit.
rem SimpleITK, pandas und pyarrow braucht nur die Entwicklung, nicht das Programm.
"%PYTHON%" -m PyInstaller --noconfirm --clean --windowed ^
    --name AKICHEAST3D ^
    --paths "%~dp0src" ^
    --distpath "%~dp0dist" ^
    --workpath "%~dp0build" ^
    --specpath "%~dp0build" ^
    --copy-metadata pylibjpeg ^
    --copy-metadata pylibjpeg-libjpeg ^
    --copy-metadata pylibjpeg-openjpeg ^
    --hidden-import libjpeg ^
    --hidden-import openjpeg ^
    --exclude-module SimpleITK ^
    --exclude-module pandas ^
    --exclude-module pyarrow ^
    --exclude-module IPython ^
    --exclude-module tkinter ^
    --exclude-module idc_index ^
    --exclude-module duckdb ^
    --exclude-module pytest ^
    "%~dp0src\akicheast3d\main.py"
if errorlevel 1 (
    echo Build fehlgeschlagen.
    exit /b 1
)

rem Zwischendateien entfernen, damit nur die fertige .exe in dist\ übrig bleibt
rmdir /s /q "%~dp0build"

echo Selbsttest der .exe mit einem komprimierten Phantom ...
set "SELFTEST=%TEMP%\akicheast3d_selbsttest"
if exist "%SELFTEST%" rmdir /s /q "%SELFTEST%"
"%PYTHON%" -m tests.phantoms "%SELFTEST%" >nul
start "" /wait "%~dp0dist\AKICHEAST3D\AKICHEAST3D.exe" --selbsttest "%SELFTEST%\kugel_komprimiert" "%SELFTEST%\bild.png"
if errorlevel 1 (
    type "%SELFTEST%\bild.txt"
    echo Selbsttest fehlgeschlagen.
    exit /b 1
)
rmdir /s /q "%SELFTEST%"

echo Fertig: dist\AKICHEAST3D\AKICHEAST3D.exe
