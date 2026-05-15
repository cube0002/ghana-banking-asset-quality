# Installation Guide

## System Requirements
- Python 3.9+
- pip or conda
- Git

## Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/ghana-banking-analysis.git
cd ghana-banking-analysis
```

## Step 2: Create Virtual Environment (macOS/Linux)
```bash
python3.11 -m venv venv
source venv/bin/activate
```

## Step 3: Create Virtual Environment (Windows)
```cmd
python -m venv venv
venv\Scripts\activate
```

## Step 4: Install Package
```bash
pip install -e ".[dev]"
```

## Step 5: Verify Installation
```bash
python -c "import ghana_banking; print(ghana_banking.__version__)"
pytest tests/ -v
```

## Troubleshooting

**ModuleNotFoundError: No module named 'ghana_banking'**
```bash
pip install -e .
```

**statsmodels import fails**
```bash
pip install --upgrade statsmodels
```

**Jupyter kernel not found**
```bash
python -m ipykernel install --user --name ghana --display-name "Ghana Banking"
jupyter lab  # Then select "Ghana Banking" kernel
```
