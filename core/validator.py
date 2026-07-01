"""Módulo de validación para TextZipLab.

Proporciona la comparación estricta byte a byte para garantizar que la
compresión sea realmente sin pérdida.
"""

from __future__ import annotations
from pathlib import Path


def comparar_archivos_byte_a_byte(ruta1: str, ruta2: str) -> bool:
    """Compara el archivo original y el descomprimido byte a byte.

    Devuelve True si son idénticos, de lo contrario False.
    """
    p1, p2 = Path(ruta1), Path(ruta2)
    if not p1.exists() or not p2.exists():
        return False
    with p1.open("rb") as f1, p2.open("rb") as f2:
        return f1.read() == f2.read()
