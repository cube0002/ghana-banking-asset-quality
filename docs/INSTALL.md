# Installation

## Requirements

- Python 3.9 or newer
- Git
- pip

## Clone the repository

```bash
git clone https://github.com/cube0002/ghana-banking-asset-quality.git
cd ghana-banking-asset-quality
```

## Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install dependencies

```bash
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
```

## Verify the installation

```bash
python -c "import ghana_banking; print(ghana_banking.__version__)"
pytest tests/ -v
```

The project reads the source CSV files from `data/raw/` by default. If you keep the data elsewhere, pass that directory to `load_banking_data(raw_data_path=...)`.

## Open the notebooks

```bash
jupyter lab notebooks/
```

Run the notebooks in numerical order. The notebooks document the analysis; the Python package provides reusable functions.
