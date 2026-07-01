"""Implementación académica de compresión Huffman."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import heapq
from typing import Optional

from .bit_utils import add_padding
from .metrics import get_original_size_bits


@dataclass
class HuffmanNode:
    """Nodo del árbol de Huffman."""
    char: Optional[str]
    freq: int
    left: Optional["HuffmanNode"] = None
    right: Optional["HuffmanNode"] = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class HuffmanCompressor:
    """Compresor/descompresor Huffman para texto plano."""

    def compress(self, text: str) -> dict:
        """Comprime un texto y devuelve los datos necesarios para descomprimir."""
        original_size_bits = get_original_size_bits(text)

        if text == "":
            return {
                "algorithm": "Huffman",
                "original_text": text,
                "encoded_text": "",
                "codes": {},
                "tree": None,
                "frequencies": {},
                "original_size_bits": 0,
                "compressed_size_bits": 0,
                "bitstream_size_bits": 0,
                "overhead_size_bits": 0,
                "padding": 0,
                "symbol_count": 0,
            }

        frequencies = dict(Counter(text))
        tree = self._build_tree(frequencies)
        codes: dict[str, str] = {}
        self._generate_codes(tree, "", codes)

        encoded_text = "".join(codes[ch] for ch in text)
        _, padding = add_padding(encoded_text)

        bitstream_size_bits = len(encoded_text) + padding
        overhead_size_bits = self._estimate_overhead_bits(codes)
        compressed_size_bits = bitstream_size_bits + overhead_size_bits

        return {
            "algorithm": "Huffman",
            "original_text": text,
            "encoded_text": encoded_text,
            "codes": codes,
            "tree": tree,
            "frequencies": frequencies,
            "original_size_bits": original_size_bits,
            "compressed_size_bits": compressed_size_bits,
            "bitstream_size_bits": bitstream_size_bits,
            "overhead_size_bits": overhead_size_bits,
            "padding": padding,
            "symbol_count": len(codes),
        }

    def decompress(self, compressed_data: dict) -> str:
        """Descomprime datos generados por compress."""
        encoded_text = compressed_data.get("encoded_text", "")
        frequencies = compressed_data.get("frequencies", {})
        tree = compressed_data.get("tree")
        codes = compressed_data.get("codes", {})

        if not encoded_text:
            return ""

        # Reconstruir el árbol y códigos si se cargó de archivo (solo frecuencias disponibles)
        if tree is None and frequencies:
            tree = self._build_tree(frequencies)
            codes = {}
            self._generate_codes(tree, "", codes)

        if tree is not None:
            # Caso especial: un único símbolo repetido.
            if tree.is_leaf():
                return tree.char * len(encoded_text)

            result: list[str] = []
            current = tree
            for bit in encoded_text:
                current = current.left if bit == "0" else current.right
                if current is None:
                    raise ValueError("Bitstream Huffman inválido.")
                if current.is_leaf():
                    result.append(current.char)
                    current = tree
            return "".join(result)

        # Fallback por tabla de códigos si el árbol no se conserva.
        reverse_codes = {code: char for char, code in codes.items()}
        result: list[str] = []
        buffer = ""
        for bit in encoded_text:
            buffer += bit
            if buffer in reverse_codes:
                result.append(reverse_codes[buffer])
                buffer = ""

        if buffer:
            raise ValueError("Bitstream Huffman incompleto o tabla inválida.")
        return "".join(result)

    def _build_tree(self, frequencies: dict[str, int]) -> HuffmanNode:
        heap: list[tuple[int, int, HuffmanNode]] = []
        counter = 0

        for char, freq in frequencies.items():
            heapq.heappush(heap, (freq, counter, HuffmanNode(char=char, freq=freq)))
            counter += 1

        while len(heap) > 1:
            freq_a, _, left = heapq.heappop(heap)
            freq_b, _, right = heapq.heappop(heap)
            parent = HuffmanNode(char=None, freq=freq_a + freq_b, left=left, right=right)
            heapq.heappush(heap, (parent.freq, counter, parent))
            counter += 1

        return heap[0][2]

    def _generate_codes(self, node: HuffmanNode, prefix: str, codes: dict[str, str]) -> None:
        if node.is_leaf():
            # Si solo existe un símbolo, se le asigna "0".
            codes[node.char] = prefix or "0"
            return

        if node.left is not None:
            self._generate_codes(node.left, prefix + "0", codes)
        if node.right is not None:
            self._generate_codes(node.right, prefix + "1", codes)

    def _estimate_overhead_bits(self, codes: dict[str, str]) -> int:
        """Estima el costo de guardar la tabla de códigos.

        Se aproxima como: símbolo UTF-8 + longitud del código + bits del código.
        No busca ser un formato ZIP real, sino una métrica experimental justa.
        """
        overhead = 0
        for char, code in codes.items():
            overhead += len(char.encode("utf-8")) * 8
            overhead += 8  # longitud del código almacenada en un byte
            overhead += len(code)
        return overhead
