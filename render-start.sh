echo "=== Starting initialization at $(date) ==="
python -m scripts.initialize || { echo "Initialization failed"; exit 1; }
echo "=== Initialization succeeded at $(date) ==="
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
