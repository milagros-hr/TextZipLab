import tempfile
from pathlib import Path
import pytest
import json

from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.file_manager import (
    save_compressed_file,
    load_compressed_file,
    validate_compressed_data,
    preview_compressed_data,
)

def test_huffman_json_serialization_cycle():
    original_text = "hola mundo con huffman y unicode! 🚀 áéíóú ñ"
    compressor = HuffmanCompressor()
    
    compressed_data = compressor.compress(original_text)
    compressed_data["original_extension"] = ".csv"
    compressed_data["original_encoding"] = "utf-8"
    compressed_data["original_name"] = "datos.csv"
    compressed_data["original_size_bytes"] = len(original_text.encode("utf-8"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "test_huffman.huff.json"
        
        save_compressed_file(str(temp_path), compressed_data)
        assert temp_path.exists()
        
        loaded_data = load_compressed_file(str(temp_path))
        assert loaded_data["algorithm"] == "Huffman"
        assert validate_compressed_data(loaded_data) is True
        assert loaded_data.get("original_extension") == ".csv"
        assert loaded_data.get("original_encoding") == "utf-8"
        assert loaded_data.get("original_name") == "datos.csv"
        assert loaded_data.get("original_size_bytes") == len(original_text.encode("utf-8"))
        
        recovered_text = compressor.decompress(loaded_data)
        assert recovered_text == original_text
        assert len(recovered_text.encode("utf-8")) > 0

def test_huffman_real_binary_serialization_cycle():
    original_text = "hola mundo con huffman binario real! 🚀"
    compressor = HuffmanCompressor()
    compressed_data = compressor.compress(original_text)
    
    compressed_data["original_extension"] = ".json"
    compressed_data["original_encoding"] = "utf-8"
    compressed_data["original_name"] = "config.json"
    compressed_data["original_size_bytes"] = len(original_text.encode("utf-8"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "test_huffman.huff"
        
        save_compressed_file(str(temp_path), compressed_data)
        assert temp_path.exists()
        
        # Verificar cabecera mágica física
        with open(temp_path, "rb") as f:
            bytes_start = f.read(6)
            assert bytes_start == b"TZHUF1"
            
        loaded_data = load_compressed_file(str(temp_path))
        assert loaded_data["algorithm"] == "Huffman"
        assert validate_compressed_data(loaded_data) is True
        assert loaded_data.get("original_extension") == ".json"
        assert loaded_data.get("original_encoding") == "utf-8"
        assert loaded_data.get("original_name") == "config.json"
        assert loaded_data.get("original_size_bytes") == len(original_text.encode("utf-8"))
        
        recovered_text = compressor.decompress(loaded_data)
        assert recovered_text == original_text
        assert len(recovered_text.encode("utf-8")) > 0

def test_lzw_json_serialization_cycle():
    original_text = "hola mundo con lzw y unicode! 🚀"
    compressor = LZWCompressor()
    compressed_data = compressor.compress(original_text, bit_size=12)
    compressed_data["original_extension"] = ".txt"
    compressed_data["original_encoding"] = "utf-8"
    compressed_data["original_name"] = "documento.txt"
    compressed_data["original_size_bytes"] = len(original_text.encode("utf-8"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "test_lzw.lzw.json"
        
        save_compressed_file(str(temp_path), compressed_data)
        assert temp_path.exists()
        
        loaded_data = load_compressed_file(str(temp_path))
        assert loaded_data["algorithm"] == "LZW"
        assert validate_compressed_data(loaded_data) is True
        assert loaded_data.get("original_extension") == ".txt"
        assert loaded_data.get("original_encoding") == "utf-8"
        assert loaded_data.get("original_name") == "documento.txt"
        assert loaded_data.get("original_size_bytes") == len(original_text.encode("utf-8"))
        
        recovered_text = compressor.decompress(loaded_data)
        assert recovered_text == original_text
        assert len(recovered_text.encode("utf-8")) > 0

def test_lzw_real_binary_serialization_cycle():
    original_text = "hola mundo con lzw binario real! 🚀"
    compressor = LZWCompressor()
    compressed_data = compressor.compress(original_text, bit_size=12)
    compressed_data["original_extension"] = ".csv"
    compressed_data["original_encoding"] = "utf-8"
    compressed_data["original_name"] = "valores.csv"
    compressed_data["original_size_bytes"] = len(original_text.encode("utf-8"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "test_lzw.lzw"
        
        save_compressed_file(str(temp_path), compressed_data)
        assert temp_path.exists()
        
        # Verificar cabecera mágica física
        with open(temp_path, "rb") as f:
            bytes_start = f.read(6)
            assert bytes_start == b"TZLZW1"
            
        loaded_data = load_compressed_file(str(temp_path))
        assert loaded_data["algorithm"] == "LZW"
        assert validate_compressed_data(loaded_data) is True
        assert loaded_data.get("original_extension") == ".csv"
        assert loaded_data.get("original_encoding") == "utf-8"
        assert loaded_data.get("original_name") == "valores.csv"
        assert loaded_data.get("original_size_bytes") == len(original_text.encode("utf-8"))
        
        recovered_text = compressor.decompress(loaded_data)
        assert recovered_text == original_text
        assert len(recovered_text.encode("utf-8")) > 0

def test_legacy_binary_compatibility():
    # Simular cabecera antigua HUF\x01
    frequencies = {"a": 2, "b": 1}
    freq_json = json.dumps(frequencies).encode("utf-8")
    freq_len = len(freq_json)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        legacy_path = Path(tmpdir) / "legacy.huff"
        with open(legacy_path, "wb") as f:
            f.write(b"HUF\x01")
            f.write(bytes([0])) # padding
            f.write(freq_len.to_bytes(4, byteorder="big"))
            f.write(freq_json)
            # bits empaquetados para "aab"
            f.write(b"\x00") 
            
        loaded_data = load_compressed_file(str(legacy_path))
        assert loaded_data["algorithm"] == "Huffman"
        assert loaded_data.get("original_extension") is None
        assert loaded_data.get("original_name") is None
        assert loaded_data.get("original_size_bytes") is None
        assert loaded_data.get("compressed_size_bits") is None
        
        preview = preview_compressed_data(loaded_data)
        assert "Nombre Original: No disponible" in preview
        assert "Tamaño Original Físico: No disponible" in preview

def test_invalid_serialization_data():
    invalid_data = {
        "algorithm": "Huffman",
        "encoded_text": "010101"
    }
    assert validate_compressed_data(invalid_data) is False
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / "invalid.huff.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)
            
        with pytest.raises(ValueError, match="no tiene una estructura válida"):
            load_compressed_file(str(temp_path))
