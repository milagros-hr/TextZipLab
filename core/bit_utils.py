"""Utilidades simples para manejar cadenas de bits.

En este proyecto académico se conserva el bitstream como texto "0"/"1" para
facilitar la inspección y las pruebas. Estas funciones permiten empaquetarlo
cuando se desea estimar o guardar una representación binaria real.
"""

from __future__ import annotations


def add_padding(bit_string: str) -> tuple[str, int]:
    """Completa el bitstream hasta múltiplo de 8 y devuelve el padding usado."""
    if not bit_string:
        return "", 0

    padding = (8 - (len(bit_string) % 8)) % 8
    return bit_string + ("0" * padding), padding


def remove_padding(bit_string: str, padding: int) -> str:
    """Elimina bits de relleno agregados al final del bitstream."""
    if padding < 0 or padding > 7:
        raise ValueError("El padding debe estar entre 0 y 7 bits.")
    if padding == 0:
        return bit_string
    return bit_string[:-padding]


def bits_to_bytes(bit_string: str) -> bytes:
    """Convierte una cadena de bits en bytes."""
    padded, _ = add_padding(bit_string)
    if not padded:
        return b""
    return bytes(int(padded[i:i + 8], 2) for i in range(0, len(padded), 8))


def bytes_to_bits(data: bytes) -> str:
    """Convierte bytes en una cadena de bits."""
    return "".join(f"{byte:08b}" for byte in data)
