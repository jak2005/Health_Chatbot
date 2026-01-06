echo Starting Health Chatbot...
echo.

cd /d "c:\Users\mhmdt\Downloads\Health_Chatbot-main"

if not exist "venv\Scripts\python.exe" (
    echo Error: venv not found or incomplete!
    echo Please make sure the virtual environment is set up correctly.
    pause
    exit /b
)

echo Launching application...
".\venv\Scripts\python.exe" scripts/launcher.py

if errorlevel 1 (
    echo.
    echo Application failed to start.
    pause
)
