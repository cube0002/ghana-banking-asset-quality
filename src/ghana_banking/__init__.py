"""Ghana Banking Asset Quality Analysis Package."""

__version__ = "1.0.0"
__author__ = "Your Name"

from .data.loaders import load_banking_data
from .modeling.regression import OLSModel
from .modeling.var_model import VARModel
from .modeling.stress_test import StressTest

__all__ = [
    "load_banking_data",
    "OLSModel",
    "VARModel",
    "StressTest",
]
