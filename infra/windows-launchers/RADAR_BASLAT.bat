@echo off
setlocal

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%"

title MOBIL RADAR SISTEMI - BASLATILIYOR
color 0A

echo ===================================================
echo   MOBIL RADAR SISTEMI - OTOYOL DEVRIYE MODU
echo ===================================================
echo.
echo Sistem konfigurasyonu yukleniyor...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi. Lutfen Python'u yukleyin.
    popd
    pause
    exit /b 1
)

python apps\radar-cli\run.py %*
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Sistem beklenmedik sekilde kapandi.
    popd
    pause
    exit /b 1
)

popd
endlocal
