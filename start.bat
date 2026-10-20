@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PYTHON%"
set "HOST_ADDRESS=%~1"
set "PORT=%~2"

if not defined PYTHON_EXE set "PYTHON_EXE=python"
if not defined HOST_ADDRESS set "HOST_ADDRESS=127.0.0.1"
if not defined PORT set "PORT=8000"

"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
	echo Python was not found. Activate a virtual environment or set the PYTHON environment variable. 1>&2
	exit /b 1
)

if not exist "%PROJECT_ROOT%.env" (
	echo Missing .env. Create it from .env.example before starting the project. 1>&2
	exit /b 1
)

cd /d "%PROJECT_ROOT%"

echo Using Python:
"%PYTHON_EXE%" -c "import sys; print(sys.executable)"
echo Applying database migrations...
"%PYTHON_EXE%" manage.py migrate --noinput
if errorlevel 1 exit /b %errorlevel%

echo Collecting static files...
"%PYTHON_EXE%" manage.py collectstatic --noinput
if errorlevel 1 exit /b %errorlevel%

echo Starting Django at http://%HOST_ADDRESS%:%PORT%/
"%PYTHON_EXE%" manage.py runserver "%HOST_ADDRESS%:%PORT%"
exit /b %errorlevel%
