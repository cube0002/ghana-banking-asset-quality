# Usage Guide

## Running the Full Analysis

### 1. Download Data (one-time)
```bash
python data/download_data.py
```

### 2. Start Jupyter
```bash
make notebooks
# or
jupyter lab notebooks/
```

### 3. Run Notebooks in Order
- `01_EDA.ipynb` – Exploratory analysis
- `02_Regression.ipynb` – OLS results
- `03_VAR_Modeling.ipynb` – Dynamic analysis
- `04_StressTest.ipynb` – Scenario analysis

## Using the Package Programmatically

```python
from ghana_banking import load_banking_data, OLSModel, StressTest

# Load data
df = load_banking_data()

# Fit OLS model
model = OLSModel()
model.fit(df, y_col="NPL_Ratio", x_cols=["Policy_Rate", "CPI", ...])

# Stress test
stress = StressTest(model)
stress.set_baseline(df.iloc[-1])
results = stress.run_scenarios()
print(results)
```

## Running Tests
```bash
make test
make lint
make format
```

## Common Commands
```bash
make help      # Show all available commands
make test      # Run tests with coverage
make lint      # Check code quality
make format    # Auto-format code
make clean     # Remove cache files
```
