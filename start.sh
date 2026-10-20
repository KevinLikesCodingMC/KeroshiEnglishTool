#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
host_address=${1:-127.0.0.1}
port=${2:-8000}

if [ -n "${PYTHON:-}" ]; then
	python_exe=$PYTHON
elif command -v python >/dev/null 2>&1; then
	python_exe=python
elif command -v python3 >/dev/null 2>&1; then
	python_exe=python3
else
	echo "Python was not found. Activate a virtual environment or set the PYTHON environment variable." >&2
	exit 1
fi

if [ ! -f "$project_root/.env" ]; then
	echo "Missing .env. Create it from .env.example before starting the project." >&2
	exit 1
fi

cd "$project_root"

echo "Using Python: $("$python_exe" -c 'import sys; print(sys.executable)')"
echo "Applying database migrations..."
"$python_exe" manage.py migrate --noinput

echo "Collecting static files..."
"$python_exe" manage.py collectstatic --noinput

echo "Starting Django at http://$host_address:$port/"
exec "$python_exe" manage.py runserver "$host_address:$port"
