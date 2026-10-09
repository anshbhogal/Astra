"""Temporal Splitter for Time-Series Test Run Data."""

from typing import List, Dict, Any, Tuple
import pandas as pd


class TemporalSplitter:
    """
    Splits test execution DataFrames strictly by time/run order to prevent future data leakage.
    Train: Older runs (0% to train_ratio)
    Val: Subsequent runs (train_ratio to train_ratio + val_ratio)
    Test: Latest runs (remaining)
    """

    @staticmethod
    def split_by_run_chronology(
        df: pd.DataFrame,
        time_column: str = "created_at",
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if df.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Ensure sorted chronologically by time or run ID order
        sorted_df = df.sort_values(by=time_column, ascending=True).reset_index(drop=True)
        total_rows = len(sorted_df)

        train_end = int(total_rows * train_ratio)
        val_end = int(total_rows * (train_ratio + val_ratio))

        train_df = sorted_df.iloc[:train_end].copy()
        val_df = sorted_df.iloc[train_end:val_end].copy()
        test_df = sorted_df.iloc[val_end:].copy()

        return train_df, val_df, test_df
