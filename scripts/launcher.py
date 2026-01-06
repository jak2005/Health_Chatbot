"""
HealthLink AI Launcher
Starts both the FastAPI backend and Streamlit frontend
"""

import subprocess
import time
import sys
import os
import urllib.request
import urllib.error


def is_backend_ready(url="http://localhost:8080/health"):
    """Check if the FastAPI backend is ready"""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.getcode() == 200
    except urllib.error.URLError:
        return False
    except Exception:
        return False


def main():
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = os.path.join(current_dir, "venv", "Scripts", "python.exe")
    streamlit_exe = os.path.join(current_dir, "venv", "Scripts", "streamlit.exe")
    
    # Use new FastAPI backend (main.py)
    backend_script = os.path.join(current_dir, "backend", "main.py")
    frontend_script = os.path.join(current_dir, "frontend", "streamlit_app.py")

    if not os.path.exists(python_exe):
        print(f"Error: Python executable not found at {python_exe}")
        input("Press Enter to exit...")
        sys.exit(1)

    print("=" * 50)
    print("   HealthLink AI - Starting Application")
    print("=" * 50)
    print()
    
    print("[1/2] Starting FastAPI Backend...")
    
    # Start Backend in a new window using uvicorn
    backend_cmd = f'start "HealthLink AI Backend" "{python_exe}" -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload'
    subprocess.run(backend_cmd, shell=True, cwd=os.path.join(current_dir, "backend"))

    print("[...] Waiting for backend to initialize...")
    
    # Poll backend
    max_retries = 30  # Wait up to 30 seconds
    backend_ready = False
    
    for i in range(max_retries):
        if is_backend_ready():
            backend_ready = True
            break
        print(f"      Waiting... ({i+1}/{max_retries})")
        time.sleep(1)

    if backend_ready:
        print("[OK]  Backend is ready!")
        print()
        print("[2/2] Starting Streamlit Frontend...")
        time.sleep(1)
        
        frontend_cmd = f'start "HealthLink AI Frontend" "{streamlit_exe}" run "{frontend_script}"'
        subprocess.run(frontend_cmd, shell=True)
        
        print()
        print("=" * 50)
        print("   Application Started Successfully!")
        print("=" * 50)
        print()
        print("   Backend:  http://localhost:8080")
        print("   API Docs: http://localhost:8080/docs")
        print("   Frontend: http://localhost:8501")
        print()
        print("   Press Ctrl+C in the terminal windows to stop.")
        print()
    else:
        print()
        print("[ERROR] Backend failed to start within the timeout period.")
        print("        Please check the backend console window for errors.")
        print()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
