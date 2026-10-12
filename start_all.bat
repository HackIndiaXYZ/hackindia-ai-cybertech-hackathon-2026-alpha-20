@echo off
cd /d "%~dp0"
start "MedTriage backend" cmd /k start_backend.bat
start "MedTriage frontend" cmd /k start_frontend.bat
timeout /t 6 >nul
start "" http://127.0.0.1:5173
echo Both servers were started in separate windows. Close those windows to stop them.
