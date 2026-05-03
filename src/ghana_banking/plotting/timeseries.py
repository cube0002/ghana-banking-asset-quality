"""Plotting functions for banking sector time series."""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib.dates as mdates
from typing import Optional, Tuple, List


def plot_npl_timeline(
    df: pd.DataFrame,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple = (14, 7),
    show_events: bool = True
) -> plt.Axes:
    """Plot NPL ratio over time with key events marked.
    
    Shows the NPL journey from 2010 to present, highlighting major events
    like banking reforms, the IMF program, and COVID.
    
    Args:
        df: Data indexed by date with 'Non Performing Loan Ratio' column
        ax: Matplotlib axes to draw on (creates new if None)
        figsize: Figure size
        show_events: Whether to annotate reforms, elections, etc.
    
    Returns:
        The axes object
    
    Example:
        fig, ax = plt.subplots(figsize=(14, 7))
        plot_npl_timeline(df, ax=ax)
        plt.tight_layout()
        plt.show()
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize, dpi=100)
    
    # Main NPL line
    ax.plot(
        df.index,
        df['Non Performing Loan Ratio'],
        color='#2C3E50',
        linewidth=3,
        label='NPL Ratio (%)',
        zorder=4
    )
    
    # Fill under line
    ax.fill_between(
        df.index,
        df['Non Performing Loan Ratio'],
        color='#34495E',
        alpha=0.1
    )
    
    if show_events:
        # Banking cleanup period
        ax.axvspan(
            pd.to_datetime('2017-08-01'),
            pd.to_datetime('2019-12-31'),
            color='#F1C40F',
            alpha=0.15,
            label='Sector Reform/Cleanup'
        )
        
        # Key events with annotations
        events = [
            ("IMF Program", '2015-04-03', 18),
            ("COVID-19 Arrival", '2020-03-12', 12),
            ("DDEP Launch", '2022-12-05', 14)
        ]
        
        for label, date_str, y_pos in events:
            date = pd.to_datetime(date_str)
            ax.axvline(date, color='#7F8C8D', linestyle=':', linewidth=1.5, zorder=2)
            ax.annotate(
                label,
                xy=(date, y_pos),
                xytext=(30, 0),
                textcoords='offset points',
                arrowprops=dict(arrowstyle='-|>'),
                fontsize=9,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8)
            )
        
        # Elections
        election_dates = ['2012-12-07', '2016-12-07', '2020-12-07', '2024-12-07']
        for d in election_dates:
            dt = pd.to_datetime(d)
            ax.axvline(dt, color='#E74C3C', linestyle='--', alpha=0.5, linewidth=1, zorder=1)
            ax.text(
                dt,
                ax.get_ylim()[1] * 0.97,
                'Election',
                color='#E74C3C',
                fontsize=7,
                ha='right',
                va='top',
                rotation=90,
                fontweight='bold'
            )
        
        # Prudential limit
        ax.axhline(10, color='#27AE60', linestyle='-.', alpha=0.6, label='Prudential Limit (Ref)')
    
    # Formatting
    ax.set_title(
        "Timeline of Ghana's Banking Sector NPLs (2010 - 2025)",
        fontsize=16,
        fontweight='bold',
        pad=20
    )
    ax.set_ylabel("Non-Performing Loans (% of Gross Loans)", fontsize=11)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.legend(loc='upper left', fontsize=10, frameon=True)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    return ax


def plot_correlation_heatmap(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    figsize: Tuple = (10, 8),
    cmap: str = 'coolwarm'
) -> plt.Figure:
    """
    Plot correlation heatmap of specified variables.
    
    Parameters
    ----------
    df : pd.DataFrame
        Data containing variables to correlate.
    cols : list, optional
        Columns to include. If None, uses all numeric columns.
    figsize : tuple, default (10, 8)
        Figure size.
    cmap : str, default 'coolwarm'
        Colormap for heatmap.
    
    Returns
    -------
    plt.Figure
        The figure object.
    
    Examples
    --------
    >>> fig = plot_correlation_heatmap(df, cols=['NPL', 'Rate', 'GDP', 'CPI'])
    >>> plt.show()
    """
    if cols is None:
        cols = df.select_dtypes(include=['number']).columns.tolist()
    
    # Calculate correlation
    corr_matrix = df[cols].corr()
    
    # Create plot
    fig, ax = plt.subplots(figsize=figsize, dpi=100)
    
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt='.2f',
        cmap=cmap,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={'label': 'Correlation'},
        ax=ax,
        vmin=-1,
        vmax=1
    )
    
    ax.set_title('Correlation Matrix Heatmap', fontsize=14, fontweight='bold', pad=15)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    
    return fig


def plot_dual_axis(
    df: pd.DataFrame,
    left_col: str,
    right_col: str,
    figsize: Tuple = (14, 6),
    left_color: str = '#2C3E50',
    right_color: str = '#E67E22'
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot two variables on different y-axes when scales don't match.
    
    Useful for comparing variables with different ranges:
    e.g., NPL ratio (5-28%) vs Policy Rate (8-30%) - both fit nicely.
    
    Args:
        df: Data indexed by date
        left_col: Variable for left y-axis
        right_col: Variable for right y-axis
        figsize: Figure size
        left_color: Color for left line
        right_color: Color for right line
    
    Returns:
        Figure and left axes
    
    Example:
        fig, ax1 = plot_dual_axis(df, 'NPL_Ratio', 'Policy_Rate')
        # Both variables visible on same timeline
    """
    left_col : str
        Column name for left y-axis.
    right_col : str
        Column name for right y-axis.
    figsize : tuple, default (14, 6)
        Figure size.
    left_color : str
        Color for left axis line.
    right_color : str
        Color for right axis line.
    
    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
        Figure and axes objects.
    
    Examples
    --------
    >>> fig, ax = plot_dual_axis(df, 'NPL_Ratio', 'Policy_Rate')
    >>> plt.show()
    """
    fig, ax1 = plt.subplots(figsize=figsize, dpi=100)
    
    # Left axis
    ax1.plot(df.index, df[left_col], color=left_color, linewidth=2.5, label=left_col)
    ax1.set_ylabel(left_col, color=left_color, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=left_color)
    
    # Right axis
    ax2 = ax1.twinx()
    ax2.plot(df.index, df[right_col], color=right_color, linewidth=2.5, linestyle='--', label=right_col)
    ax2.set_ylabel(right_col, color=right_color, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=right_color)
    
    # Title and formatting
    ax1.set_title(f'{left_col} vs {right_col}', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    fig.tight_layout()
    
    return fig, ax1


def plot_distributions(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    figsize: Tuple = (16, 10)
) -> plt.Figure:
    """Plot histograms of multiple variables to see their distribution.
    
    Good for spotting outliers, skewness, or unusual patterns.
    Shows mean and median as reference lines.
    
    Args:
        df: Data with variables
        cols: Which variables to plot (None = first 4 numeric)
        figsize: Figure size
    
    Returns:
        The figure object
    
    Example:
        fig = plot_distributions(df, cols=['NPL', 'Rate', 'GDP', 'CPI'])
        # See if variables are normally distributed or skewed
    """
    if cols is None:
        cols = df.select_dtypes(include=['number']).columns.tolist()[:4]
    
    n_cols = len(cols)
    n_rows = (n_cols + 1) // 2
    
    fig, axes = plt.subplots(n_rows, 2, figsize=figsize, dpi=100)
    axes = axes.flatten()
    
    for idx, col in enumerate(cols):
        ax = axes[idx]
        sns.histplot(df[col], kde=True, ax=ax, color='#3498DB', alpha=0.6, bins=20)
        
        # Add mean and median lines
        mean_val = df[col].mean()
        median_val = df[col].median()
        ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
        ax.axvline(median_val, color='green', linestyle='-.', linewidth=2, label=f'Median: {median_val:.2f}')
        
        ax.set_title(f'Distribution of {col}', fontweight='bold')
        ax.legend(fontsize=9)
    
    # Remove extra subplots
    for idx in range(n_cols, len(axes)):
        fig.delaxes(axes[idx])
    
    plt.suptitle('Variable Distributions', fontsize=16, fontweight='bold', y=1.00)
    fig.tight_layout()
    
    return fig
