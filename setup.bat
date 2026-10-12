@echo off
REM One-time setup. Safe to re-run. Never overwrites an existing .env file.
cd /d "%~dp0"

echo === Backend: virtual environment and dependencies ===
if not exist venv\Scripts\python.exe (
  py -3.12 -m venv venv || py -3 -m venv venv || (echo Could not create venv. Install Python 3.11/3.12. & exit /b 1)
)
venv\Scripts\python.exe -m pip install -r requirements.txt || (echo pip install failed & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example. EDIT .env and add GROQ_API_KEY for AI + voice features.
) else (
  echo .env already exists - left untouched.
)

echo === Frontend: dependencies ===
cd frontend
call npm install || (echo npm install failed. Install Node.js 18+ from nodejs.org & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  echo Created frontend\.env from .env.example.
)
cd ..
echo.
echo Setup complete. Run start_all.bat to launch backend + frontend.
