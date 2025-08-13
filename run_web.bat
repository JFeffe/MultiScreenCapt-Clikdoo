@echo off
setlocal

REM Ensure venv exists
if not exist .\.venv\Scripts\python.exe (
    echo [setup] Creating virtual environment...
    py -3.13 -m venv .venv || goto :error
)

echo [setup] Upgrading pip...
".\.venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error

echo [setup] Installing requirements (fastapi/uvicorn/etc.)...
".\.venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error

REM Configure Tcl/Tk for Tkinter if needed by underlying libs
set "TCL_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6"
set "TK_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tk8.6"

echo [run] Starting server at http://127.0.0.1:8000/
".\.venv\Scripts\python.exe" -m uvicorn web_server:app --host 127.0.0.1 --port 8000 --reload
goto :eof

:error
echo.
echo [error] Web setup failed. See messages above.
exit /b 1



