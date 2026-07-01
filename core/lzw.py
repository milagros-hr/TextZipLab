"""Implementación académica de compresión LZW."""

from __future__ import annotations

from .metrics import get_original_size_bits


class LZWCompressor:
    """Compresor/descompresor LZW para texto plano."""

    def compress(self, text: str, bit_size: int = 12) -> dict:
        """Comprime texto usando LZW con diccionario limitado por bit_size."""
        if bit_size <= 0:
            raise ValueError("bit_size debe ser positivo.")

        original_size_bits = get_original_size_bits(text)

        if text == "":
            return {
                "algorithm": "LZW",
                "original_text": text,
                "codes": [],
                "bit_size": bit_size,
                "dictionary_size": 0,
                "alphabet": [],
                "original_size_bits": 0,
                "compressed_size_bits": 0,
            }

        max_dictionary_size = 2 ** bit_size
        alphabet = sorted(set(text))
        dictionary = {char: index for index, char in enumerate(alphabet)}
        next_code = len(dictionary)

        w = ""
        output_codes: list[int] = []

        for char in text:
            wc = w + char
            if wc in dictionary:
                w = wc
            else:
                if w:
                    output_codes.append(dictionary[w])
                if next_code < max_dictionary_size:
                    dictionary[wc] = next_code
                    next_code += 1
                w = char

        if w:
            output_codes.append(dictionary[w])

        return {
            "algorithm": "LZW",
            "original_text": text,
            "codes": output_codes,
            "bit_size": bit_size,
            "dictionary_size": len(dictionary),
            "alphabet": alphabet,
            "original_size_bits": original_size_bits,
            "compressed_size_bits": len(output_codes) * bit_size,
        }

    def decompress(self, compressed_data: dict) -> str:
        """Descomprime datos generados por compress."""
        codes = compressed_data.get("codes", [])
        bit_size = compressed_data.get("bit_size", 12)
        alphabet = compressed_data.get("alphabet", [])

        if not codes:
            return ""

        max_dictionary_size = 2 ** bit_size
        dictionary = {index: char for index, char in enumerate(alphabet)}
        next_code = len(dictionary)

        first_code = codes[0]
        if first_code not in dictionary:
            raise ValueError("Código inicial LZW inválido.")

        w = dictionary[first_code]
        result = [w]

        for code in codes[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                # Caso especial clásico de LZW: KwKwK.
                entry = w + w[0]
            else:
                raise ValueError("Código LZW inválido.")

            result.append(entry)

            if next_code < max_dictionary_size:
                dictionary[next_code] = w + entry[0]
                next_code += 1

            w = entry

        return "".join(result)
