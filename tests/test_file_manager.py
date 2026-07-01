from core.file_manager import (
    ensure_text_file,
    get_file_size_bits,
    get_file_size_bytes,
    read_text_file,
)


def test_file_size_matches_windows_size_field_for_crlf(tmp_path):
    path = tmp_path / "sample.txt"
    raw = b"linea 1\r\nlinea 2\r\nlinea 3"
    path.write_bytes(raw)

    text = read_text_file(str(path))

    assert text == "linea 1\r\nlinea 2\r\nlinea 3"
    assert get_file_size_bytes(str(path)) == len(raw)
    assert get_file_size_bits(str(path)) == len(raw) * 8
    assert len(text.encode("utf-8")) * 8 == get_file_size_bits(str(path))


def test_textual_extensions_are_allowed(tmp_path):
    path = tmp_path / "data.csv"
    path.write_bytes(b"a,b,c\n1,2,3")

    assert ensure_text_file(str(path)) is True
    assert read_text_file(str(path)) == "a,b,c\n1,2,3"
