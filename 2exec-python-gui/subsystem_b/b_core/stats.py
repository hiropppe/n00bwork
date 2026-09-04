"""B の本体ロジック: 数値列の統計量を計算する純粋関数。

numpy 依存。この依存こそが「A に import させたくない重めの依存」の代役。
"""

from __future__ import annotations

import numpy as np


class BadInputError(ValueError):
    """入力（params）が不正なときに送出する。worker が BAD_INPUT に変換する。"""


def compute(values: list[float]) -> dict[str, float]:
    """数値列に対して mean/std/min/max/median を計算して返す。

    Args:
        values: 数値の配列。空でないこと。

    Returns:
        {"mean", "std", "min", "max", "median"} を含む dict。

    Raises:
        BadInputError: values が配列でない / 空 / 数値でない要素を含む場合。
    """
    if not isinstance(values, list):
        raise BadInputError("values must be a list of numbers")
    if len(values) == 0:
        raise BadInputError("values must not be empty")
    for v in values:
        # bool は int のサブクラスだが数値として扱わない
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise BadInputError("values must be numbers")

    arr = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise BadInputError("values must be finite numbers")

    # population std（ddof=0）。返り値は素の float にして JSON 化を安全にする。
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
    }
