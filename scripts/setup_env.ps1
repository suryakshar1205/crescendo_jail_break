# Crescendo Jailbreak Defense — Environment Setup (PowerShell)
# Usage: .\scripts\setup_env.ps1

Write-Host "=== Crescendo Defense — Environment Setup ===" -ForegroundColor Cyan

# 1. Create virtual environment if it doesn't exist
if (-Not (Test-Path ".\venv")) {
    Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "[1/4] Virtual environment already exists." -ForegroundColor Green
}

# 2. Activate virtual environment
Write-Host "[2/4] Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# 3. Install dependencies
Write-Host "[3/4] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

# 4. Verify installation
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow
python -c "import torch; import transformers; import sentence_transformers; import numpy; import psutil; print('All dependencies verified successfully.')"

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "To run the full pipeline:"
Write-Host "  python scripts/run_full_pipeline.py --mock_inference   # Quick validation"
Write-Host "  python scripts/run_full_pipeline.py                    # Full benchmark"
Write-Host ""
Write-Host "To run tests:"
Write-Host "  python -m pytest tests/"
