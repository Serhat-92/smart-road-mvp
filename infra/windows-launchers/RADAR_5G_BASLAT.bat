@echo off
setlocal
cls

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%"

title 5G MOBIL RADAR BASLATICI - PROFESYONEL MOD
color 0f

echo ==========================================================
echo   MOBIL RADAR SISTEMI - 5G BAGLANTILI MOD (v2.0)
echo ==========================================================
echo.
echo [1/3] GEREKLI KUTUPHANELER KONTROL EDILIYOR...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Kutuphaneler yuklenirken hata olustu veya pip bulunamadi.
    echo     Internet baglantinizi kontrol edin.
) else (
    echo [OK] Kutuphaneler hazir.
)

echo.
echo [2/3] KOMUTA MERKEZI BASLATILIYOR...
start "5G KOMUTA MERKEZI (HQ)" cmd /k "cd /d %REPO_ROOT% && python apps\command-center\server.py"
timeout /t 2 >nul

echo.
echo [3/3] RADAR SISTEMI BASLATILIYOR...
echo.
echo SECENEKLER:
echo 1. WEBKAMERA MODU
echo 2. DONANIM MODU
echo 3. FULL SIMULASYON MODU
echo.
set /p secim="Mod Seciniz (1-3) [Varsayilan: 3]: "

if "%secim%"=="" set secim=3

if "%secim%"=="1" (
    python apps\radar-cli\main.py --source 0 --server http://127.0.0.1:8000 --max_speed 90 --evidence_dir datasets\violations
)

if "%secim%"=="2" (
    set /p radar_port="Radar Portu Girin (orn: COM3): "
    python apps\radar-cli\main.py --source 0 --server http://127.0.0.1:8000 --port %radar_port% --max_speed 90 --evidence_dir datasets\violations
)

if "%secim%"=="3" (
    python apps\radar-cli\main.py --source 0 --server http://127.0.0.1:8000 --port MOCK --max_speed 90 --evidence_dir datasets\violations
)

echo.
echo Sistem kapatildi.
popd
pause
endlocal
