"""Diagnostic plots for checking if models are reasonable."""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional, Tuple


def plot_residuals(
    model_results,
    figsize: Tuple = (14, 10),
    title: str = "OLS Regression Diagnostics"
) -> Tuple[plt.Figure, np.ndarray]:
    """Create the classic 4-panel diagnostic plot for regression.
    
    Checks if the model is behaving itself:
    - Top left: No pattern in errors (should be random scatter)
    - Top right: Errors are normally distributed (should follow the line)
    - Bottom left: Variance is constant (should be flat band)
    - Bottom right: Distribution of errors (should be bell-shaped)
    
    Args:
        model_results: Fitted statsmodels OLS result
        figsize: Figure size
        title: Plot title
    
    Returns:
        Figure and axes array
    
    Example:
        fig, axes = plot_residuals(ols_model.results)
        plt.tight_layout()
        plt.show()
    """
    residuals = model_results.resid
    fitted_values = model_results.fittedvalues
    standardized_residuals = residuals / np.std(residuals)
    
    fig, axes = plt.subplots(2, 2, figsize=figsize, dpi=100)
    
    # 1. Residuals vs Fitted Values
    axes[0, 0].scatter(fitted_values, residuals, alpha=0.6, s=50, color='steelblue')
    axes[0, 0].axhline(y=0, color='red', linestyle='--', linewidth=2)
    axes[0, 0].set_xlabel('Fitted Values')
    axes[0, 0].set_ylabel('Residuals')
    axes[0, 0].set_title('Residuals vs Fitted Values', fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Q-Q Plot (Normality)
    stats.probplot(residuals, dist="norm", plot=axes[0, 1])
    axes[0, 1].set_title('Normal Q-Q Plot', fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Scale-Location (Homoscedasticity)
    sqrt_abs_std_residuals = np.sqrt(np.abs(standardized_residuals))
    axes[1, 0].scatter(fitted_values, sqrt_abs_std_residuals, alpha=0.6, s=50, color='steelblue')
    axes[1, 0].set_xlabel('Fitted Values')
    axes[1, 0].set_ylabel('√|Standardized Residuals|')
    axes[1, 0].set_title('Scale-Location Plot', fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Residuals Histogram
    axes[1, 1].hist(residuals, bins=20, edgecolor='black', alpha=0.7, color='steelblue')
    axes[1, 1].axvline(x=0, color='red', linestyle='--', linewidth=2)
    axes[1, 1].set_xlabel('Residuals')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Residuals Histogram', fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    fig.suptitle(title, fontsize=16, fontweight='bold', y=1.00)
    fig.tight_layout()
    
    return fig, axes


def plot_acf_pacf(
    residuals: np.ndarray,
    lags: int = 20,
    figsize: Tuple = (14, 5)
) -> Tuple[plt.Figure, np.ndarray]:
    """Plot autocorrelation to check for time dependency in errors.
    
    If there's autocorrelation (spikes outside the shaded region),
    it means errors aren't random - the model is missing something.
    
    Args:
        residuals: Model errors
        lags: How many time periods to check
        figsize: Figure size
    
    Returns:
        Figure and axes array
    
    Example:
        fig, axes = plot_acf_pacf(residuals, lags=24)
        # Spikes = dependencies to investigate
        # All in shaded region = good, errors are random
    """
    --------
    >>> from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    >>> resid = model.resid
    >>> fig, axes = plot_acf_pacf(resid, lags=20)
    >>> plt.show()
    """
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    
    fig, axes = plt.subplots(1, 2, figsize=figsize, dpi=100)
    
    # ACF plot
    plot_acf(residuals, lags=lags, ax=axes[0])
    axes[0].set_title('Autocorrelation Function (ACF)', fontweight='bold')
    axes[0].set_xlabel('Lag')
    axes[0].set_ylabel('ACF')
    axes[0].grid(True, alpha=0.3)
    
    # PACF plot
    plot_pacf(residuals, lags=lags, ax=axes[1], method='ywm')
    axes[1].set_title('Partial Autocorrelation Function (PACF)', fontweight='bold')
    axes[1].set_xlabel('Lag')
    axes[1].set_ylabel('PACF')
    axes[1].grid(True, alpha=0.3)
    
    fig.suptitle('Autocorrelation Analysis of Residuals', fontsize=14, fontweight='bold')
    fig.tight_layout()
    
    return fig, axes


def plot_irf(
    irf_matrix: np.ndarray,
    variable_names: list,
    periods: int = 12,
    figsize: Tuple = (16, 10),
    title: str = "Impulse Response Functions (IRF)"
) -> Tuple[plt.Figure, np.ndarray]:
    """Visualize how shocks ripple through the system over time.
    
    Each panel shows: "If this variable gets shocked, how do others respond?"
    Useful for understanding economic spillovers and contagion.
    
    Args:
        irf_matrix: Full 3D impulse response array from VAR model
        variable_names: Names of the variables
        periods: Number of months to show
        figsize: Figure size
        title: Plot title
    
    Returns:
        Figure and axes grid
    
    Example:
        fig, axes = plot_irf(irf.irfs, ['NPL', 'Rate', 'GDP'], periods=12)
        # Each row = shock to one variable
        # Each column = response of one variable
    """
    title : str
        Plot title.
    
    Returns
    -------
    Tuple[plt.Figure, np.ndarray]
        Figure and axes array.
    
    Examples
    --------
    >>> irf = var_model.irf(periods=12)
    >>> fig, axes = plot_irf(irf.irfs, ['NPL', 'Rate', 'GDP'], periods=12)
    >>> plt.show()
    """
    n_vars = len(variable_names)
    fig, axes = plt.subplots(n_vars, n_vars, figsize=figsize, dpi=100)
    
    if n_vars == 1:
        axes = np.array([[axes]])
    elif n_vars > 1:
        if axes.ndim == 1:
            axes = axes.reshape(1, -1)
    
    for response_idx in range(n_vars):
        for impulse_idx in range(n_vars):
            ax = axes[response_idx, impulse_idx]
            
            # Extract IRF values
            irf_values = irf_matrix[:, response_idx, impulse_idx]
            
            # Plot
            ax.plot(range(len(irf_values)), irf_values, linewidth=2, color='darkblue')
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax.fill_between(range(len(irf_values)), irf_values, alpha=0.3, color='steelblue')
            
            # Labels
            if response_idx == n_vars - 1:
                ax.set_xlabel(f'Shock to: {variable_names[impulse_idx]}', fontweight='bold')
            if impulse_idx == 0:
                ax.set_ylabel(f'Response of:\n{variable_names[response_idx]}', fontweight='bold')
            
            ax.grid(True, alpha=0.3)
    
    fig.suptitle(title, fontsize=16, fontweight='bold')
    fig.tight_layout()
    
    return fig, axes


def plot_stress_results(
    stress_results: pd.DataFrame,
    figsize: Tuple = (12, 6),
    title: str = "Stress Testing Results"
) -> plt.Figure:
    """Plot scenario outcomes side by side for easy comparison.
    
    See at a glance: baseline NPL, mild stress NPL, crisis NPL, etc.
    
    Args:
        stress_results: DataFrame from stress_test.run_scenarios()
        figsize: Figure size
        title: Plot title
    
    Returns:
        The figure object
    
    Example:
        results = st.run_scenarios(scenarios)
        fig = plot_stress_results(results)
        # Shows bars: Baseline (green), Crisis (red), etc.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    
    # Get predicted NPL column
    pred_col = [col for col in stress_results.columns if 'Predicted' in col][0]
    
    # Color mapping
    colors = {
        'Baseline': '#2ecc71',
        'Moderate Tightening': '#f1c40f',
        'Severe Currency Crisis': '#e74c3c',
        'Severe Recession': '#e67e22'
    }
    
    bar_colors = [colors.get(s, '#3498db') for s in stress_results['Scenario']]
    
    # Create bars
    bars = ax.bar(
        range(len(stress_results)),
        stress_results[pred_col],
        color=bar_colors,
        edgecolor='black',
        linewidth=1.5,
        alpha=0.85
    )
    
    # Add value labels on bars
    for bar, value in zip(bars, stress_results[pred_col]):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.3,
            f'{value:.2f}%',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )
    
    # Formatting
    ax.set_xticks(range(len(stress_results)))
    ax.set_xticklabels(stress_results['Scenario'], rotation=15, ha='right')
    ax.set_ylabel('Predicted Value', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3)
    
    fig.tight_layout()
    
    return fig


def plot_sensitivity_analysis(
    sensitivity_df: pd.DataFrame,
    variable_col: str,
    pred_col: str,
    figsize: Tuple = (10, 6)
) -> plt.Figure:
    """Plot how sensitive NPL is to one variable over a range.
    
    Shows the relationship: if this variable goes from X to Y,
    how much does NPL go up or down? Helps identify which variables
    are the "dials you should watch."
    
    Args:
        sensitivity_df: Results from sensitivity_analysis()
        variable_col: Which variable is being shocked
        pred_col: The prediction column to plot
        figsize: Figure size
    
    Returns:
        The figure object
    
    Example:
        sens = st.sensitivity_analysis(base, 'Rate', range_pct=0.3)
        fig = plot_sensitivity_analysis(sens, 'Rate', 'Predicted_NPL')
        # Rising line = rate increases hurt NPLs
        # Flat line = rate doesn't matter much
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    
    ax.plot(
        sensitivity_df[variable_col],
        sensitivity_df[pred_col],
        linewidth=2.5,
        marker='o',
        markersize=6,
        color='darkblue',
        label='Sensitivity'
    )
    
    ax.fill_between(
        sensitivity_df[variable_col],
        sensitivity_df[pred_col],
        alpha=0.3,
        color='steelblue'
    )
    
    # Formatting
    ax.set_xlabel(variable_col, fontsize=12, fontweight='bold')
    ax.set_ylabel(pred_col, fontsize=12, fontweight='bold')
    ax.set_title(f'Sensitivity Analysis: {variable_col}', fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    fig.tight_layout()
    
    return fig
