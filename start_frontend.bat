@echo off
cd /d "%~dp0frontend"
if not exist node_modules (echo Run setup.bat first. & pause & exit /b 1)
echo Frontend: http://127.0.0.1:5173
call npm run dev
