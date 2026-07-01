"""Pruebas unitarias para casos especiales en TextZipLab."""

from __future__ import annotations

from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.metrics import measure_algorithm


def run_roundtrip_test(text: str):
    """Auxiliar para verificar que ambos algoritmos comprimen y descomprimen sin pérdida."""
    for compressor in [HuffmanCompressor(), LZWCompressor()]:
        # Ejecutar a través de measure_algorithm para validar flujo completo y guardado
        result = measure_algorithm(compressor, text)
        assert result["lossless"] is True
        assert result["decompressed_text"] == text


def test_empty_text():
    run_roundtrip_test("")


def test_single_repeated_char():
    run_roundtrip_test("A" * 1000)


def test_many_repeated_words():
    run_roundtrip_test("hola mundo repetido " * 500)


def test_text_with_tildes():
    run_roundtrip_test("Esta es una prueba con tildes: á, é, í, ó, ú, Á, É, Í, Ó, Ú, ñ, Ñ, ü, Ü.")


def test_text_with_emojis():
    run_roundtrip_test("Hola 🐍 🚀 💻 Compresión sin pérdida! 🔥")


def test_text_with_korean():
    run_roundtrip_test("안녕하세요! 텍스트 압축 테스트입니다. 한국어 지원 확인.")


def test_csv_format():
    csv_content = (
        "id,nombre,edad,pais\n"
        "1,Mila,22,Peru\n"
        "2,Juan,25,Argentina\n"
        "3,Sofia,30,Colombia\n"
    )
    run_roundtrip_test(csv_content)


def test_json_format():
    json_content = '{"nombre": "TextZipLab", "versión": 1.0, "soportado": true, "caracteres": ["á", "🚀", "한"]}'
    run_roundtrip_test(json_content)


def test_large_text():
    # Caso de texto más grande para pruebas rápidas en unit tests
    large_text = "Dato de prueba repetido " * 10000
    run_roundtrip_test(large_text)
