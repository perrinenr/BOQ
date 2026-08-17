@echo off
setlocal

cd /d "%~dp0"

echo ================================================
echo      BUILD BOQ IMPORTER
echo ================================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv was not found.
    echo Create it first with:
    echo py -3.12 -m venv .venv
    pause
    exit /b 1
)

echo.
echo Activating Python 3.12 virtual environment...
call ".venv\Scripts\activate.bat"

echo.
echo Python version:
python --version

echo.
echo Python architecture:
python -c "import struct; print(str(struct.calcsize('P') * 8) + '-bit')"

echo.
echo Updating build tools...
python -m pip install --upgrade pip setuptools wheel pyinstaller

echo.
echo Cleaning old builds...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "BOQ_Importer.spec" del /q "BOQ_Importer.spec"

echo.
echo Building executable...

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name "BOQ_Importer" ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    --hidden-import pyodbc ^
    --hidden-import openpyxl ^
    --hidden-import xlrd ^
    --hidden-import pdfplumber ^
    --hidden-import ezdxf ^
    --hidden-import dotenv ^
    --hidden-import pydantic ^
    --hidden-import openai ^
    app.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo BUILD FAILED
    echo ================================================
    pause
    exit /b 1
)

echo.
echo Copying configuration files...

if exist ".env" (
    copy /y ".env" "dist\BOQ_Importer\.env" >nul
)

if exist "assets" (
    xcopy /e /i /y "assets" "dist\BOQ_Importer\assets" >nul
)

echo.
echo ================================================
echo BUILD COMPLETED
echo ================================================
echo.
echo Run:
echo dist\BOQ_Importer\BOQ_Importer.exe
echo.

pause