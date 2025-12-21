@echo off
chcp 65001 >nul
cls

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    UFT-BILSEM EXE BUILD                      ║
echo ║                                                              ║
echo ║  Bu script hem DEBUG hem de RELEASE versiyonlarını           ║
echo ║  oluşturacaktır.                                             ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Python kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ HATA: Python bulunamadı!
    echo Lütfen Python'u sisteminize yükleyin.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Gerekli paketler kontrolü
echo 🔍 Gerekli paketler kontrol ediliyor...
python -c "import streamlit, PyInstaller, requests, PyPDF2, docx" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Gerekli paketler eksik, yükleniyor...
    pip install -r requirements_build.txt
    if %errorlevel% neq 0 (
        echo ❌ Paket yüklenemedi!
        pause
        exit /b 1
    )
    echo ✅ Gerekli paketler yüklendi.
    echo.
)

REM UPX kontrolü
echo 🔍 UPX kontrol ediliyor...
upx --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  UPX bulunamadı. Dosya boyutu büyük olabilir.
    echo UPX yüklemek için: https://upx.github.io/
    echo.
) else (
    echo ✅ UPX bulundu, dosyalar sıkıştırılacak.
    echo.
)

echo ════════════════════════════════════════════════════════════════
echo 🛠️  DEBUG versiyon oluşturuluyor...
echo ════════════════════════════════════════════════════════════════
python build_debug.py
if %errorlevel% neq 0 (
    echo ❌ DEBUG build başarısız oldu!
    pause
    exit /b 1
)

echo.
echo ════════════════════════════════════════════════════════════════
echo 🛠️  RELEASE versiyon oluşturuluyor...
echo ════════════════════════════════════════════════════════════════
python build.py
if %errorlevel% neq 0 (
    echo ❌ RELEASE build başarısız oldu!
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🎉 TAMAMLANDI!                            ║
echo ║                                                              ║
echo ║  Oluşturulan dosyalar:                                       ║
echo ║    • dist/UFT-BILSEM-DEBUG.exe  (Debug versiyon)             ║
echo ║    • dist/UFT-BILSEM.exe        (Release versiyon)           ║
echo ║                                                              ║
echo ║  Not: Release versiyonu daha küçük boyutludur ve             ║
echo ║       konsolu gizlidir.                                      ║
echo ╚══════════════════════════════════════════════════════════════╝

REM Dosya boyutlarını göster
if exist "dist\UFT-BILSEM-DEBUG.exe" (
    for %%A in ("dist\UFT-BILSEM-DEBUG.exe") do (
        set size_debug=%%~zA
    )
    set /a size_debug_mb=%size_debug%/1024/1024
    echo.
    echo 📊 DEBUG EXE boyutu: %size_debug_mb% MB
)

if exist "dist\UFT-BILSEM.exe" (
    for %%A in ("dist\UFT-BILSEM.exe") do (
        set size_release=%%~zA
    )
    set /a size_release_mb=%size_release%/1024/1024
    echo 📊 RELEASE EXE boyutu: %size_release_mb% MB
)

echo.
echo 🚀 Uygulamaları çalıştırmak için:
echo    dist\UFT-BILSEM-DEBUG.exe   (Hata ayıklama için)
echo    dist\UFT-BILSEM.exe         (Normal kullanım için)
echo.
pause
