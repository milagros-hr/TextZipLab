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
    """Guarda datos comprimidos usando un formato binario compacto para Huffman y LZW,
    o en formato JSON legible si la ruta termina en '.json'.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    if path.lower().endswith(".json"):
        # Copiar datos para evitar guardar objetos no serializables como HuffmanNode
        clean_data = {}
        for k, v in compressed_data.items():
            if k == "tree":
                continue  # El árbol se puede reconstruir a partir de frecuencias
            clean_data[k] = v
        with target.open("w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
        return

    alg = compressed_data.get("algorithm")
    
    if alg == "Huffman":
        # Formato binario real (magic b"TZHUF1"):
        # [Magic 6B: TZHUF1]
        # [ExtLen 1B] [Ext string]
        # [EncLen 1B] [Enc string]
        # [NameLen 1B] [Name string]
        # [OrigSizeBytes 8B]
        # [LogicalCompBits 8B]
        # [Padding 1B]
        # [FreqEntriesNum 4B]
        # Loop FreqEntriesNum:
        #   [CharLen 1B] [Char bytes] [Freq 4B]
        # [Bitstream bytes]
        ext = compressed_data.get("original_extension")
        ext = ext.encode("utf-8") if ext is not None else b".txt"
        
        enc = compressed_data.get("original_encoding")
        enc = enc.encode("utf-8") if enc is not None else b"utf-8"
        
        name = compressed_data.get("original_name")
        name = name.encode("utf-8") if name is not None else b"archivo_recuperado"
        
        orig_size_bytes = int(compressed_data.get("original_size_bytes", 0))
        logical_comp_bits = int(compressed_data.get("compressed_size_bits", 0))
        
        padding = compressed_data.get("padding", 0)
        frequencies = compressed_data.get("frequencies", {})
        encoded_text = compressed_data.get("encoded_text", "")
        
        from core.bit_utils import bits_to_bytes
        bit_bytes = bits_to_bytes(encoded_text)
        
        with target.open("wb") as f:
            f.write(b"TZHUF1")
            f.write(bytes([len(ext)]))
            f.write(ext)
            f.write(bytes([len(enc)]))
            f.write(enc)
            f.write(bytes([len(name)]))
            f.write(name)
            f.write(orig_size_bytes.to_bytes(8, byteorder="big"))
            f.write(logical_comp_bits.to_bytes(8, byteorder="big"))
            f.write(bytes([padding]))
            
            f.write(len(frequencies).to_bytes(4, byteorder="big"))
            for char, freq in frequencies.items():
                char_bytes = char.encode("utf-8")
                f.write(bytes([len(char_bytes)]))
                f.write(char_bytes)
                f.write(freq.to_bytes(4, byteorder="big"))
                
            f.write(bit_bytes)
            
    elif alg == "LZW":
        # Formato binario real (magic b"TZLZW1")
        # [Magic 6B: TZLZW1]
        # [ExtLen 1B] [Ext string]
        # [EncLen 1B] [Enc string]
        # [NameLen 1B] [Name string]
        # [OrigSizeBytes 8B]
        # [LogicalCompBits 8B]
        # [BitSize 1B]
        # [AlpLen 4B]
        # Loop AlpLen:
        #   [CharLen 1B] [Char bytes]
        # [NumCodes 4B]
        # [Packed codes]
        ext = compressed_data.get("original_extension")
        ext = ext.encode("utf-8") if ext is not None else b".txt"
        
        enc = compressed_data.get("original_encoding")
        enc = enc.encode("utf-8") if enc is not None else b"utf-8"
        
        name = compressed_data.get("original_name")
        name = name.encode("utf-8") if name is not None else b"archivo_recuperado"
        
        orig_size_bytes = int(compressed_data.get("original_size_bytes", 0))
        logical_comp_bits = int(compressed_data.get("compressed_size_bits", 0))
        
        bit_size = compressed_data.get("bit_size", 12)
        alphabet = compressed_data.get("alphabet", [])
        codes = compressed_data.get("codes", [])
        
        bit_string = "".join(f"{code:0{bit_size}b}" for code in codes)
        from core.bit_utils import bits_to_bytes
        packed_bytes = bits_to_bytes(bit_string)
        
        with target.open("wb") as f:
            f.write(b"TZLZW1")
            f.write(bytes([len(ext)]))
            f.write(ext)
            f.write(bytes([len(enc)]))
            f.write(enc)
            f.write(bytes([len(name)]))
            f.write(name)
            f.write(orig_size_bytes.to_bytes(8, byteorder="big"))
            f.write(logical_comp_bits.to_bytes(8, byteorder="big"))
            f.write(bytes([bit_size]))
            
            f.write(len(alphabet).to_bytes(4, byteorder="big"))
            for char in alphabet:
                char_bytes = char.encode("utf-8")
                f.write(bytes([len(char_bytes)]))
                f.write(char_bytes)
                
            f.write(len(codes).to_bytes(4, byteorder="big"))
            f.write(packed_bytes)
            
    else:
        # Fallback a pickle con cabecera PKL\x01
        with target.open("wb") as f:
            f.write(b"PKL\x01")
            pickle.dump(compressed_data, f)


def load_compressed_file(path: str) -> dict[str, Any]:
    """Carga y descomprime el formato binario o JSON a un diccionario compatible."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"El archivo no existe: {path}")

    if path.lower().endswith(".json"):
        with target.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not validate_compressed_data(data):
            raise ValueError("El archivo comprimido JSON no tiene una estructura válida o requerida.")
        return data

    with target.open("rb") as f:
        magic_4 = f.read(4)
        if magic_4 == b"TZHU":
            f.read(2)  # Leer F1
            ext_len = int(f.read(1)[0])
            ext = f.read(ext_len).decode("utf-8")
            enc_len = int(f.read(1)[0])
            enc = f.read(enc_len).decode("utf-8")
            name_len = int(f.read(1)[0])
            name = f.read(name_len).decode("utf-8")
            orig_size_bytes = int.from_bytes(f.read(8), byteorder="big")
            logical_comp_bits = int.from_bytes(f.read(8), byteorder="big")
            padding = int(f.read(1)[0])
            
            freq_entries = int.from_bytes(f.read(4), byteorder="big")
            frequencies = {}
            for _ in range(freq_entries):
                char_len = int(f.read(1)[0])
                char = f.read(char_len).decode("utf-8")
                freq = int.from_bytes(f.read(4), byteorder="big")
                frequencies[char] = freq
                
            bit_bytes = f.read()
            from core.bit_utils import bytes_to_bits, remove_padding
            raw_bits = bytes_to_bits(bit_bytes)
            encoded_text = remove_padding(raw_bits, padding)
            
            return {
                "algorithm": "Huffman",
                "frequencies": frequencies,
                "padding": padding,
                "encoded_text": encoded_text,
                "original_extension": ext,
                "original_encoding": enc,
                "original_name": name,
                "original_size_bytes": orig_size_bytes,
                "original_size_bits": orig_size_bytes * 8,
                "compressed_size_bits": logical_comp_bits,
            }
            
        elif magic_4 == b"TZLZ":
            f.read(2)  # Leer W1
            ext_len = int(f.read(1)[0])
            ext = f.read(ext_len).decode("utf-8")
            enc_len = int(f.read(1)[0])
            enc = f.read(enc_len).decode("utf-8")
            name_len = int(f.read(1)[0])
            name = f.read(name_len).decode("utf-8")
            orig_size_bytes = int.from_bytes(f.read(8), byteorder="big")
            logical_comp_bits = int.from_bytes(f.read(8), byteorder="big")
            bit_size = int(f.read(1)[0])
            
            alp_len = int.from_bytes(f.read(4), byteorder="big")
            alphabet = []
            for _ in range(alp_len):
                char_len = int(f.read(1)[0])
                char = f.read(char_len).decode("utf-8")
                alphabet.append(char)
                
            num_codes = int.from_bytes(f.read(4), byteorder="big")
            packed_bytes = f.read()
            
            from core.bit_utils import bytes_to_bits
            raw_bits = bytes_to_bits(packed_bytes)
            
            codes = []
            for i in range(num_codes):
                start = i * bit_size
                code_bits = raw_bits[start:start + bit_size]
                if len(code_bits) == bit_size:
                    codes.append(int(code_bits, 2))
                    
            return {
                "algorithm": "LZW",
                "bit_size": bit_size,
                "alphabet": alphabet,
                "codes": codes,
                "original_extension": ext,
                "original_encoding": enc,
                "original_name": name,
                "original_size_bytes": orig_size_bytes,
                "original_size_bits": orig_size_bytes * 8,
                "compressed_size_bits": logical_comp_bits,
            }

        elif magic_4 == b"HUF\x01":
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
                "original_extension": None,
                "original_encoding": None,
                "original_name": None,
                "original_size_bytes": None,
                "original_size_bits": None,
                "compressed_size_bits": None,
            }
            
        elif magic_4 == b"LZW\x01":
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
                "original_extension": None,
                "original_encoding": None,
                "original_name": None,
                "original_size_bytes": None,
                "original_size_bits": None,
                "compressed_size_bits": None,
            }
            
        elif magic_4 == b"PKL\x01":
            return pickle.load(f)
        else:
            # Reintentar cargar directamente para compatibilidad
            f.seek(0)
            return pickle.load(f)


def validate_compressed_data(compressed_data: dict[str, Any]) -> bool:
    """Valida que los datos comprimidos tengan la estructura requerida."""
    if not isinstance(compressed_data, dict):
        return False
    alg = compressed_data.get("algorithm")
    if alg not in {"Huffman", "LZW"}:
        return False
    if alg == "Huffman":
        if "encoded_text" not in compressed_data or "frequencies" not in compressed_data or "padding" not in compressed_data:
            return False
        if not isinstance(compressed_data["encoded_text"], str):
            return False
        if not isinstance(compressed_data["frequencies"], dict):
            return False
        if not isinstance(compressed_data["padding"], int):
            return False
    elif alg == "LZW":
        if "codes" not in compressed_data or "alphabet" not in compressed_data or "bit_size" not in compressed_data:
            return False
        if not isinstance(compressed_data["codes"], list):
            return False
        if not isinstance(compressed_data["alphabet"], list):
            return False
        if not isinstance(compressed_data["bit_size"], int):
            return False
    return True


def preview_compressed_data(compressed_data: dict[str, Any], max_items: int = 20) -> str:
    """Genera una vista previa textual compacta de la estructura comprimida."""
    if not validate_compressed_data(compressed_data):
        return "Error: Estructura de datos comprimidos no válida."
    
    alg = compressed_data.get("algorithm")
    orig_bytes = compressed_data.get("original_size_bytes")
    comp_bits = compressed_data.get("compressed_size_bits")
    ext = compressed_data.get("original_extension")
    enc = compressed_data.get("original_encoding")
    name = compressed_data.get("original_name")
    
    preview = []
    preview.append(f"Algoritmo: {alg}")
    preview.append(f"Nombre Original: {name if name is not None else 'No disponible'}")
    preview.append(f"Extensión Original: {ext if ext is not None else 'No disponible'}")
    preview.append(f"Codificación Original: {enc if enc is not None else 'No disponible'}")
    preview.append(f"Tamaño Original Físico: {f'{orig_bytes:,} bytes' if orig_bytes is not None else 'No disponible'}")
    preview.append(f"Tamaño Comprimido Teórico: {f'{comp_bits:,} bits' if comp_bits is not None else 'No disponible'}")
    
    if alg == "Huffman":
        padding = compressed_data.get("padding", 0)
        encoded_text = compressed_data.get("encoded_text", "")
        codes = compressed_data.get("codes", {})
        
        # Si codes está vacío pero tenemos frecuencias, intentamos generarlo para vista previa
        if not codes and "frequencies" in compressed_data:
            try:
                from core.huffman import HuffmanCompressor
                compressor = HuffmanCompressor()
                tree = compressor._build_tree(compressed_data["frequencies"])
                codes = {}
                compressor._generate_codes(tree, "", codes)
            except Exception:
                codes = {}

        codes_preview = []
        for i, (char, code) in enumerate(codes.items()):
            if i >= max_items:
                codes_preview.append("...")
                break
            char_repr = repr(char)
            codes_preview.append(f"{char_repr}: {code}")
        
        text_preview = encoded_text[:100] + ("..." if len(encoded_text) > 100 else "")
        
        preview.append(f"Padding (bits): {padding}")
        preview.append(f"Códigos (primeros {max_items}): {', '.join(codes_preview) if codes_preview else 'No disponibles'}")
        preview.append(f"Texto Codificado Parcial: {text_preview}")
        
    elif alg == "LZW":
        bit_size = compressed_data.get("bit_size", 12)
        dict_size = compressed_data.get("dictionary_size", 0)
        codes = compressed_data.get("codes", [])
        
        codes_str = [str(c) for c in codes[:max_items]]
        if len(codes) > max_items:
            codes_str.append("...")
        
        preview.append(f"Tamaño de Bit (bit_size): {bit_size}")
        preview.append(f"Tamaño del Diccionario: {dict_size}")
        preview.append(f"Códigos Parcial: [{', '.join(codes_str)}]")
        
    return "\n".join(preview)



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
