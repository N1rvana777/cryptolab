"""目标变量计算：未来收益率。

这些列是ML训练的标签(label)，绝对不能用作特征(feature)。
LeakageGuard会强制检查这一点——如果fwd_return_*出现在特征矩阵中，立刻报错。

公式: fwd_return_Nh = close[t+N] / close[t] - 1
最后N行会是NaN（因为没有未来数据），pipeline会自动丢弃。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Target column names (used by pipeline to exclude from feature matrix)
TARGET_COLUMNS = ["fwd_return_1h", "fwd_return_4h", "fwd_return_24h"]


def compute_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add forward return columns to DataFrame.

    These represent the FUTURE returns and must never be used as features.
    """
    c = df["close"]
    df["fwd_return_1h"] = c.shift(-1) / c - 1
    df["fwd_return_4h"] = c.shift(-4) / c - 1
    df["fwd_return_24h"] = c.shift(-24) / c - 1
    return df
