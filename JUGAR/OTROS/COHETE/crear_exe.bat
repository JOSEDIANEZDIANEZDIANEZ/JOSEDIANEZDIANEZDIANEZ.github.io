@echo off
echo Instalando herramientas...
python -m pip install pyinstaller pygame-ce
echo Creando el .exe (puede tardar un par de minutos)...
python -m PyInstaller --onefile --windowed --name Cohetes main.py
echo.
echo Listo: tu juego esta en la carpeta dist\Cohetes.exe
pause
