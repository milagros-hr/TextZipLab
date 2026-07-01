from core.lzw import LZWCompressor


def test_lzw_roundtrip_simple():
    compressor = LZWCompressor()
    text = "ABRACADABRA"
    assert compressor.decompress(compressor.compress(text)) == text


def test_lzw_empty_text():
    compressor = LZWCompressor()
    data = compressor.compress("")
    assert data["codes"] == []
    assert compressor.decompress(data) == ""


def test_lzw_repetitive_text():
    compressor = LZWCompressor()
    text = "AAAAAAAAAAAAAAAAAAAA"
    assert compressor.decompress(compressor.compress(text)) == text


def test_lzw_without_clear_repetitions():
    compressor = LZWCompressor()
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert compressor.decompress(compressor.compress(text)) == text


def test_lzw_long_text():
    compressor = LZWCompressor()
    text = ("ABRACADABRA " * 1000) + "\nFIN"
    assert compressor.decompress(compressor.compress(text)) == text
