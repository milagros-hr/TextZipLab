from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from experiments.test_generator import generate_cases


def test_generated_cases_integrity():
    compressors = [HuffmanCompressor(), LZWCompressor()]
    for case in generate_cases(include_large=False):
        if case.theoretical_only:
            continue
        for compressor in compressors:
            data = compressor.compress(case.text)
            assert compressor.decompress(data) == case.text
