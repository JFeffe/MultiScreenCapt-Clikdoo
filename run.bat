@echo off
setlocal

REM Ensure venv exists
if not exist .\.venv\Scripts\python.exe (
    echo [setup] Creating virtual environment...
    py -3.13 -m venv .venv || goto :error
    echo [setup] Upgrading pip...
    .\.venv\Scripts\python -m pip install --upgrade pip || goto :error
    echo [setup] Installing requirements...
    .\.venv\Scripts\python -m pip install -r requirements.txt || goto :error
)

REM Configure Tcl/Tk for Tkinter (Python 3.13 default install path)
set "TCL_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6"
set "TK_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tk8.6"

echo [run] Starting app...
".\.venv\Scripts\python.exe" main.py
goto :eof

:error
echo.
echo [error] Setup failed. See messages above.
exit /b 1


