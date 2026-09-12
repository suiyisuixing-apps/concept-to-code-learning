@echo off
setlocal
pushd "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Project Python environment is missing. See docs\full-delivery\RUNNING.md.
  popd
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\desktop.py" --port 18766 %*
set "c2c_exit=%errorlevel%"
popd
if not "%c2c_exit%"=="0" pause
exit /b %c2c_exit%
