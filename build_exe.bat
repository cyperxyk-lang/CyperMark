@echo off
chcp 65001 >nul
echo === CyperMark — Сборка EXE ===
echo.

set PYTHONIOENCODING=utf-8

echo [1/4] Очистка...
rmdir /s /q build 2>nul
rmdir /s /q __pycache__ 2>nul
if exist dist\CyperMark.exe del /f /q dist\CyperMark.exe

echo [2/4] Установка зависимостей...
pip install -r requirements.txt

echo [3/4] Сборка...
python -m PyInstaller --onefile --windowed --name "CyperMark" ^
    --add-data "watermark_core.py;." ^
    --hidden-import "watermark_core" ^
    --hidden-import "PIL" ^
    --hidden-import "cv2" ^
    --collect-all "PIL" ^
    --noconfirm --clean main.py

echo [4/4] Готово!
echo.
echo EXE: dist\CyperMark.exe
pause
