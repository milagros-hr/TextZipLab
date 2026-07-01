"""Gestión de archivos para TextZipLab.

Este módulo trabaja con archivos textuales y comprimidos. Para que las métricas
coincidan con el campo "Tamaño" de Windows, la lectura de archivos de texto se hace
desde bytes y luego se decodifica, evitando la conversión automática de saltos de línea CRLF -> LF.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

TEXT_EXTENSIONS = {
    ".txt", ".csv", ".json", ".xml", ".html", ".htm",
    ".md", ".py", ".java", ".js", ".css", ".sql", ".log",
    ".ini", ".cfg", ".yaml", ".yml", ".c", ".cpp"
}


def ensure_text_file(path: str) -> bool:
    """Valida existencia y extensión de archivo textual soportado."""
    file_path = Path(path)
    return (
        file_path.exists()
        and file_path.is_file()
        and file_path.suffix.lower() in TEXT_EXTENSIONS
    )


def ensure_txt_file(path: str) -> bool:
    """Compatibilidad hacia atrás."""
    return ensure_text_file(path)


def get_file_size_bytes(path: str) -> int:
    """Devuelve el tamaño físico real del archivo en bytes.

    Este valor corresponde al campo "Tamaño" de Windows, no al campo
    "Tamaño en disco".
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError("El archivo no existe.")
    return file_path.stat().st_size


def get_file_size_bits(path: str) -> int:
    """Devuelve el tamaño físico real del archivo en bits."""
    return get_file_size_bytes(path) * 8


def leer_texto_con_encoding(path: str) -> tuple[str, str]:
    """Intenta leer un archivo de texto plano con UTF-8, UTF-8-SIG y Latin-1.

    No altera el contenido original (no aplica .strip() ni normaliza saltos de línea).
    Si la extensión no está permitida, lanza un ValueError con un mensaje específico.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"El archivo no existe: {path}")

    if file_path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError("Archivo no permitido. TextZipLab está diseñado para archivos de texto plano.")

    raw_bytes = file_path.read_bytes()
    encodings = ["utf-8", "utf-8-sig", "latin-1"]

    for enc in encodings:
        try:
            return raw_bytes.decode(enc), enc
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "utf-8",
        raw_bytes,
        0,
        len(raw_bytes),
        "No se pudo leer el archivo con las codificaciones disponibles (UTF-8, UTF-8-SIG, Latin-1)."
    )


def read_text_file(path: str, encoding: str = "utf-8") -> str:
    """Lee un archivo textual preservando bytes lógicos como CRLF (backward compatibility)."""
    text, _ = leer_texto_con_encoding(path)
    return text


def save_text_file(path: str, content: str, encoding: str = "utf-8") -> None:
    """Guarda contenido de texto con una codificación específica."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode(encoding))


def save_compressed_file(path: str, compressed_data: dict[str, Any]) -> None:
    """Guarda datos comprimidos usando un formato binario compacto para Huffman y LZW.

    Esto reduce a casi cero el overhead y asegura mediciones de ratio físicas realistas.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    alg = compressed_data.get("algorithm")
    
    if alg == "Huffman":
        # Formato: [Magic 4B: HUF\x01] [Padding 1B] [FreqLen 4B] [FreqJSON NB] [Bitstream bytes]
        frequencies = compressed_data.get("frequencies", {})
        padding = compressed_data.get("padding", 0)
        encoded_text = compressed_data.get("encoded_text", "")
        
        freq_json = json.dumps(frequencies).encode("utf-8")
        freq_len = len(freq_json)
        
        from core.bit_utils import bits_to_bytes
        bit_bytes = bits_to_bytes(encoded_text)
        
        with target.open("wb") as f:
            f.write(b"HUF\x01")
            f.write(bytes([padding]))
            f.write(freq_len.to_bytes(4, byteorder="big"))
            f.write(freq_json)
            f.write(bit_bytes)
            
    elif alg == "LZW":
        # Formato: [Magic 4B: LZW\x01] [BitSize 1B] [AlphabetLen 4B] [AlphabetJSON NB] [NumCodes 4B] [Codes bytes]
        bit_size = compressed_data.get("bit_size", 12)
        alphabet = compressed_data.get("alphabet", [])
        codes = compressed_data.get("codes", [])
        
        alphabet_json = json.dumps(alphabet).encode("utf-8")
        alp_len = len(alphabet_json)
        num_codes = len(codes)
        
        # Empaquetar códigos a nivel de bits
        bit_string = "".join(f"{code:0{bit_size}b}" for code in codes)
        from core.bit_utils import bits_to_bytes
        packed_bytes = bits_to_bytes(bit_string)
        
        with target.open("wb") as f:
            f.write(b"LZW\x01")
            f.write(bytes([bit_size]))
            f.write(alp_len.to_bytes(4, byteorder="big"))
            f.write(alphabet_json)
            f.write(num_codes.to_bytes(4, byteorder="big"))
            f.write(packed_bytes)
            
    else:
        # Fallback a pickle con cabecera PKL\x01
        with target.open("wb") as f:
            f.write(b"PKL\x01")
            pickle.dump(compressed_data, f)


def load_compressed_file(path: str) -> dict[str, Any]:
    """Carga y descomprime el formato binario a un diccionario compatible."""
    with Path(path).open("rb") as f:
        header = f.read(4)
        if header == b"HUF\x01":
            padding = int(f.read(1)[0])
            freq_len = int.from_bytes(f.read(4), byteorder="big")
            freq_json = f.read(freq_len)
            frequencies = json.loads(freq_json.decode("utf-8"))
            bit_bytes = f.read()
            
            from core.bit_utils import bytes_to_bits, remove_padding
            raw_bits = bytes_to_bits(bit_bytes)
            encoded_text = remove_padding(raw_bits, padding)
            
            return {
                "algorithm": "Huffman",
                "frequencies": frequencies,
                "padding": padding,
                "encoded_text": encoded_text,
            }
            
        elif header == b"LZW\x01":
            bit_size = int(f.read(1)[0])
            alp_len = int.from_bytes(f.read(4), byteorder="big")
            alphabet_json = f.read(alp_len)
            alphabet = json.loads(alphabet_json.decode("utf-8"))
            num_codes = int.from_bytes(f.read(4), byteorder="big")
            packed_bytes = f.read()
            
            from core.bit_utils import bytes_to_bits
            raw_bits = bytes_to_bits(packed_bytes)
            
            codes = []
            for i in range(0, num_codes * bit_size, bit_size):
                code_bits = raw_bits[i:i + bit_size]
                if len(code_bits) == bit_size:
                    codes.append(int(code_bits, 2))
                    
            return {
                "algorithm": "LZW",
                "bit_size": bit_size,
                "alphabet": alphabet,
                "codes": codes,
            }
            
        elif header == b"PKL\x01":
            return pickle.load(f)
        else:
            # Reintentar cargar directamente para compatibilidad
            f.seek(0)
            return pickle.load(f)


def save_results_json(path: str, results: list[dict[str, Any]]) -> None:
    """Guarda resultados en JSON, excluyendo objetos no serializables."""
    clean_results = []
    for row in results:
        clean_row = {
            k: v
            for k, v in row.items()
            if k not in {"compressed_data", "decompressed_text"}
        }
        clean_results.append(clean_row)

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(clean_results, indent=2, ensure_ascii=False), encoding="utf-8")
