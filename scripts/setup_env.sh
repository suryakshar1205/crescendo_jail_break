#!/bin/bash
# Crescendo Jailbreak Defense — Environment Setup (Bash)
# Usage: bash scripts/setup_env.sh

set -e

echo "=== Crescendo Defense — Environment Setup ==="

# 1. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/4] Virtual environment already exists."
fi

# 2. Activate virtual environment
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

# 3. Install dependencies
echo "[3/4] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 4. Verify installation
echo "[4/4] Verifying installation..."
python -c "import torch; import transformers; import sentence_transformers; import numpy; import psutil; print('All dependencies verified successfully.')"

echo ""
echo "=== Setup Complete ==="
echo "To run the full pipeline:"
echo "  python scripts/run_full_pipeline.py --mock_inference   # Quick validation"
echo "  python scripts/run_full_pipeline.py                    # Full benchmark"
echo ""
echo "To run tests:"
echo "  python -m pytest tests/"
