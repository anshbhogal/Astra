"""Data Leakage Guard & Sanity Validation."""

from typing import List, Dict, Any
import pandas as pd


class LeakageValidator:
    """
    Validates that ML feature vectors do not leak information from current or future test runs.
    """

    @staticmethod
    def assert_no_data_leakage(features_df: pd.DataFrame) -> bool:
        """
        Verifies that feature columns do not correlate 1.0 with the target outcome
        and that target columns are strictly binary (0 or 1).
        """
        if features_df.empty:
            return True

        if "target_failed" not in features_df.columns:
            raise ValueError("Dataset missing 'target_failed' column.")

        # Check target values are binary
        unique_targets = set(features_df["target_failed"].unique())
        if not unique_targets.issubset({0, 1}):
            raise ValueError(f"Target column contains non-binary values: {unique_targets}")

        # Check that no feature has perfect correlation (1.0) with target
        numeric_cols = features_df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if col == "target_failed":
                continue
            corr = features_df[col].corr(features_df["target_failed"])
            if abs(corr) >= 0.99:
                raise ValueError(f"Data leakage detected! Feature '{col}' has {corr:.4f} correlation with target.")

        return True
