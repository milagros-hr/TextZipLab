"""Métricas experimentales para TextZipLab."""

from __future__ import annotations

import os
import time
import tracemalloc
from pathlib import Path
from typing import Any

import psutil

from core.file_manager import (
    save_compressed_file,
    load_compressed_file,
    save_text_file,
    leer_texto_con_encoding,
    get_file_size_bytes,
    get_file_size_bits
)
from core.validator import comparar_archivos_byte_a_byte


def get_original_size_bits(text: str, encoding: str = "utf-8") -> int:
    """Tamaño real del texto original codificado."""
    return len(text.encode(encoding)) * 8


def measure_algorithm(
    compressor: Any,
    text: str,
    source_file_path: str | None = None,
    compressed_path: str | None = None,
    decompressed_path: str | None = None,
    **compress_kwargs: Any
) -> dict:
    """Ejecuta compress/decompress midiendo tiempo, memoria y métricas reales en disco.

    Permite guardar los archivos en rutas específicas o utilizar temporales físicos.
    """
    temp_dir = Path("temp_run")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    algo_name = compressor.__class__.__name__
    temp_orig = temp_dir / f"{algo_name}_temp_orig.txt"
    
    # Determinar rutas físicas finales
    comp_file = compressed_path if compressed_path else str(temp_dir / f"{algo_name}_temp_comp.bin")
    dec_file = decompressed_path if decompressed_path else str(temp_dir / f"{algo_name}_temp_dec.txt")
    
    encoding_usado = "utf-8"
    if source_file_path:
        try:
            _, encoding_usado = leer_texto_con_encoding(source_file_path)
        except Exception:
            encoding_usado = "utf-8"
        orig_file = source_file_path
    else:
        # Guardar en temporal si es texto manual
        save_text_file(str(temp_orig), text, encoding=encoding_usado)
        orig_file = str(temp_orig)

    original_bytes = get_file_size_bytes(orig_file)
    original_bits = original_bytes * 8

    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss

    tracemalloc.start()

    # Compresión
    start_compress = time.perf_counter()
    compressed = compressor.compress(text, **compress_kwargs)
    end_compress = time.perf_counter()
    compression_time = end_compress - start_compress

    # Guardar en archivo comprimido
    save_compressed_file(comp_file, compressed)
    compressed_bytes = get_file_size_bytes(comp_file)
    compressed_bits = compressed_bytes * 8

    # Cargar y descomprimir desde el archivo físico
    loaded_compressed = load_compressed_file(comp_file)
    
    start_decompress = time.perf_counter()
    decompressed = compressor.decompress(loaded_compressed)
    end_decompress = time.perf_counter()
    decompression_time = end_decompress - start_decompress

    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_after = process.memory_info().rss
    rss_delta = max(0, rss_after - rss_before)
    memory_used_kb = max(rss_delta, peak_memory) / 1024

    # Guardar archivo descomprimido
    save_text_file(dec_file, decompressed, encoding=encoding_usado)
    decompressed_bytes = get_file_size_bytes(dec_file)
    decompressed_bits = decompressed_bytes * 8

    # Validación byte a byte
    lossless = comparar_archivos_byte_a_byte(orig_file, dec_file)

    # Fórmulas de compresión sin división entre cero
    if original_bytes > 0:
        ratio_compresion = compressed_bytes / original_bytes
        porcentaje_comprimido = ratio_compresion * 100
        ahorro_espacio = (1.0 - ratio_compresion) * 100
    else:
        ratio_compresion = 0.0
        porcentaje_comprimido = 0.0
        ahorro_espacio = 0.0

    logical_bytes = len(text.encode(encoding_usado))
    logical_bits = logical_bytes * 8

    result = {
        "algorithm": compressed.get("algorithm", algo_name),
        "compression_time_seconds": compression_time,
        "decompression_time_seconds": decompression_time,
        "total_time_seconds": compression_time + decompression_time,
        "memory_used_kb": memory_used_kb,
        
        "original_size_bytes": original_bytes,
        "original_size_bits": original_bits,
        "compressed_size_bytes": compressed_bytes,
        "compressed_size_bits": compressed_bits,
        "decompressed_size_bytes": decompressed_bytes,
        "decompressed_size_bits": decompressed_bits,
        
        "logical_original_size_bytes": logical_bytes,
        "logical_original_size_bits": logical_bits,
        
        "compression_ratio": ratio_compresion,
        "porcentaje_comprimido": porcentaje_comprimido,
        "reduction_percentage": ahorro_espacio,
        "lossless": lossless,
        "encoding_used": encoding_usado,
        
        "compressed_data": compressed,
        "decompressed_text": decompressed,
    }

    # Preservar campos opcionales del compresor
    for key in ["dictionary_size", "symbol_count", "bitstream_size_bits", "overhead_size_bits"]:
        if key in compressed:
            result[key] = compressed[key]

    # Limpieza de archivos temporales generados si no se solicitaron explícitamente
    try:
        if not source_file_path and temp_orig.exists():
            temp_orig.unlink()
        if not compressed_path and Path(comp_file).exists():
            Path(comp_file).unlink()
        if not decompressed_path and Path(dec_file).exists():
            Path(dec_file).unlink()
    except Exception:
        pass

    return result


def summarize_result(result: dict) -> dict:
    """Devuelve una versión resumida para tablas o exportación."""
    keys = [
        "algorithm",
        "compression_time_seconds",
        "decompression_time_seconds",
        "total_time_seconds",
        "memory_used_kb",
        "original_size_bytes",
        "original_size_bits",
        "compressed_size_bytes",
        "compressed_size_bits",
        "decompressed_size_bytes",
        "decompressed_size_bits",
        "compression_ratio",
        "reduction_percentage",
        "lossless",
    ]
    return {key: result.get(key, "") for key in keys}
