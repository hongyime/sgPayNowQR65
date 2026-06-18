@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run setup first.
    exit /b 1
)
set PYTHON_CMD=.venv\Scripts\python.exe

:MENU
cls
echo ========================================================
echo            PayNow QR Generator Launcher
echo ========================================================
echo.
if exist "checkpoint.pkl" (
    echo [!] Checkpoint found. Script will resume from checkpoint.
    echo.
)

echo 1. Run / Resume (Default Settings)
echo 2. Start New Custom Range (WARNING: Deletes checkpoint)
echo 3. Delete Checkpoint Only
echo 4. Exit
echo.
set /p choice="Select an option: "

if "%choice%"=="1" goto RUN_DEFAULT
if "%choice%"=="2" goto RUN_CUSTOM
if "%choice%"=="3" goto DELETE_CHECKPOINT
if "%choice%"=="4" goto EXIT
goto MENU

:RUN_DEFAULT
"%PYTHON_CMD%" generatePayNowQR.py
pause
goto MENU

:RUN_CUSTOM
if exist "checkpoint.pkl" (
    echo Deleting existing checkpoint...
    del "checkpoint.pkl"
)
set /p start_num="Enter Start Number: "
set /p end_num="Enter End Number: "
"%PYTHON_CMD%" generatePayNowQR.py --start %start_num% --end %end_num%
pause
goto MENU

:DELETE_CHECKPOINT
if exist "checkpoint.pkl" (
    del "checkpoint.pkl"
    echo Checkpoint deleted.
) else (
    echo No checkpoint found.
)
pause
goto MENU

:EXIT
exit
