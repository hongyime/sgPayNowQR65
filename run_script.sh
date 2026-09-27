#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"
venv_dir=${VENV_DIR:-.venv-linux}
if [ ! -x "$venv_dir/bin/python" ]; then
    printf '%s\n' 'Linux environment not found. Run sh setup.sh first.' >&2
    exit 1
fi
exec "$venv_dir/bin/python" generatePayNowQR.py "$@"
