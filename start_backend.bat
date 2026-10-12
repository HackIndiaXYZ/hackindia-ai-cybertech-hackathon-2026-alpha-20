@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (echo Run setup.bat first. & pause & exit /b 1)
echo Backend: http://127.0.0.1:8000  (API docs: http://127.0.0.1:8000/docs)
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
