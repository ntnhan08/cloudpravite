@echo off
title Cloud Private - Install Dependencies

echo.
echo ================================================================
echo   CLOUD PRIVATE - INSTALL DEPENDENCIES
echo ================================================================
echo.

echo [1/3] Dang kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat!
    echo.
    echo Vui long cai Python tu: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python OK
echo.

echo [2/3] Dang kiem tra pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] pip chua co, dang cai dat...
    python -m ensurepip --upgrade
)
echo [OK] pip OK
echo.

echo [3/3] Dang cai dat dependencies...
echo.
echo [INFO] Server su dung Python standard library - KHONG CAN cai them gi!
echo.
echo Neu muon cai optional packages:
echo   pip install -r requirements.txt
echo.
echo [OK] San sang chay server!
echo.
echo Chay: start.bat
echo.
pause
