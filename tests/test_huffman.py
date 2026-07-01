from core.huffman import HuffmanCompressor


def test_huffman_roundtrip_simple():
    compressor = HuffmanCompressor()
    data = compressor.compress("ABRACADABRA")
    assert compressor.decompress(data) == "ABRACADABRA"


def test_huffman_empty_text():
    compressor = HuffmanCompressor()
    data = compressor.compress("")
    assert data["encoded_text"] == ""
    assert compressor.decompress(data) == ""


def test_huffman_single_character():
    compressor = HuffmanCompressor()
    text = "AAAAAA"
    data = compressor.compress(text)
    assert set(data["codes"].values()) == {"0"}
    assert compressor.decompress(data) == text


def test_huffman_repetitive_text():
    compressor = HuffmanCompressor()
    text = "ABCABCABCABCABC"
    assert compressor.decompress(compressor.compress(text)) == text


def test_huffman_spaces_newlines_symbols():
    compressor = HuffmanCompressor()
    text = "Hola mundo\nTexto con espacios, signos: ¿? ¡! #ADA"
    assert compressor.decompress(compressor.compress(text)) == text
