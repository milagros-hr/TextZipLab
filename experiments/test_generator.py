"""Generadores de casos de prueba para TextZipLab."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass


@dataclass
class GeneratedTestCase:
    name: str
    size: int
    text_type: str
    text: str
    theoretical_only: bool = False
    note: str = ""


def repetitive_text(size: int, char: str = "A") -> str:
    return char * size


def patterned_text(size: int, pattern: str = "ABRACADABRA") -> str:
    return (pattern * ((size // len(pattern)) + 1))[:size]


def pseudo_random_text(size: int, seed: int = 42) -> str:
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + " .,;:\n"
    return "".join(rng.choice(alphabet) for _ in range(size))


def natural_text(size: int) -> str:
    base = (
        "Los algoritmos de compresion sin perdida permiten reducir texto "
        "aprovechando frecuencias, patrones y redundancia. "
    )
    return (base * ((size // len(base)) + 1))[:size]


def code_text(size: int) -> str:
    base = (
        "def calcular_ratio(original, comprimido):\n"
        "    if comprimido == 0:\n"
        "        return 0\n"
        "    return original / comprimido\n\n"
    )
    return (base * ((size // len(base)) + 1))[:size]


def csv_text(size: int) -> str:
    rows = ["id,categoria,valor,estado\n"]
    i = 0
    while sum(len(row) for row in rows) < size:
        rows.append(f"{i},A,{i % 10},OK\n")
        i += 1
    return "".join(rows)[:size]


def generate_cases(include_large: bool = False) -> list[GeneratedTestCase]:
    """Genera casos pequeños/medianos y opcionalmente grandes.

    El caso extremo 10^10 se devuelve como teórico, sin materializar texto.
    """
    sizes = [10, 10**3]
    if include_large:
        sizes.append(10**6)

    cases: list[GeneratedTestCase] = []
    generators = [
        ("repetitivo", repetitive_text),
        ("patron", patterned_text),
        ("pseudoaleatorio", pseudo_random_text),
        ("natural", natural_text),
        ("codigo", code_text),
        ("csv", csv_text),
    ]

    for size in sizes:
        for text_type, generator in generators:
            cases.append(
                GeneratedTestCase(
                    name=f"{text_type}_{size}",
                    size=size,
                    text_type=text_type,
                    text=generator(size),
                )
            )

    cases.append(
        GeneratedTestCase(
            name="extremo_10e10_teorico",
            size=10**10,
            text_type="extremo",
            text="",
            theoretical_only=True,
            note=(
                "No se genera en memoria. Debe evaluarse por extrapolación, "
                "streaming por bloques o análisis teórico por limitación física."
            ),
        )
    )

    return cases
