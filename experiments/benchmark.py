"""Benchmark comparativo entre Huffman y LZW."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd

from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.metrics import measure_algorithm, summarize_result
from experiments.test_generator import generate_cases


RESULTS_PATH = Path("experiments/results/results.csv")


def run_benchmark(include_large: bool = False, output_path: str | Path = RESULTS_PATH) -> pd.DataFrame:
    """Ejecuta Huffman y LZW sobre los casos generados y exporta CSV."""
    rows: list[dict[str, Any]] = []
    huffman = HuffmanCompressor()
    lzw = LZWCompressor()

    for case in generate_cases(include_large=include_large):
        if case.theoretical_only:
            rows.append({
                "case_name": case.name,
                "case_size": case.size,
                "text_type": case.text_type,
                "algorithm": "Teorico",
                "note": case.note,
                "lossless": "",
            })
            continue

        for compressor in (huffman, lzw):
            result = measure_algorithm(compressor, case.text)
            row = {
                "case_name": case.name,
                "case_size": case.size,
                "text_type": case.text_type,
                **summarize_result(result),
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return df


def print_benchmark_table(df: pd.DataFrame) -> None:
    """Imprime una tabla resumida en consola."""
    visible_columns = [
        "case_name",
        "algorithm",
        "total_time_seconds",
        "memory_used_kb",
        "original_size_bits",
        "compressed_size_bits",
        "compression_ratio",
        "reduction_percentage",
        "lossless",
    ]
    existing = [col for col in visible_columns if col in df.columns]
    print(df[existing].to_string(index=False))


if __name__ == "__main__":
    dataframe = run_benchmark()
    print_benchmark_table(dataframe)
    print(f"\nResultados exportados a: {RESULTS_PATH}")
