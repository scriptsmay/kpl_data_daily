"""Analysis modules for KPL player insights generation."""

from src.analysis.metrics import compute_all as compute_metrics
from src.analysis.trends import compute_trends
from src.analysis.hero_maturity import classify_heroes
from src.analysis.growth_path import generate as generate_growth_path

__all__ = [
    "compute_metrics",
    "compute_trends",
    "classify_heroes",
    "generate_growth_path",
]
