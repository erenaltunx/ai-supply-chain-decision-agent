@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==============================================
echo  AI Supply Chain Decision Agent
echo  Windows launcher
echo ==============================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set PY=py
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set PY=python
    ) else (
        echo Python was not found.
        echo Install Python 3.10+ and enable "Add Python to PATH".
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)

echo [2/3] Installing required packages...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Starting application...
echo If the browser does not open automatically: http://localhost:8501
echo.
python -m streamlit run app.py

goto :end

:error
echo.
echo Setup failed. Review the error message above.
pause
exit /b 1

:end
endlocal
