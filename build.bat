@echo off
setlocal
cd /d "%~dp0"

echo Building CyberleekViewer portable GUI executable...

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating it...
    python -m venv .venv
    if errorlevel 1 goto :err
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :err
)

echo Installing PyInstaller...
".venv\Scripts\python.exe" -m pip install pyinstaller -q
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

echo Cleaning previous build output...
if exist "dist\CyberleekViewer.exe" del /q "dist\CyberleekViewer.exe"
if exist "dist\CyberleekViewer.zip" del /q "dist\CyberleekViewer.zip"

echo Building executable...
".venv\Scripts\python.exe" -m PyInstaller cyberleek.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    pause
    exit /b 1
)

echo Zipping the build folder...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\CyberleekViewer' -DestinationPath 'dist\CyberleekViewer.zip' -Force"
if %ERRORLEVEL% NEQ 0 (
    echo Zipping failed.
    pause
    exit /b 1
)

echo.
echo Build successful!
echo The app folder is at: dist\CyberleekViewer\CyberleekViewer.exe
echo The release zip is at: dist\CyberleekViewer.zip
echo.
pause
exit /b 0

:err
echo.
echo Setup failed. Is Python installed and on PATH?
pause
exit /b 1
