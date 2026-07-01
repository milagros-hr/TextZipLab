"""TextZipLab - orquestador principal (CLI y arranque GUI)."""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

from core.file_manager import (
    TEXT_EXTENSIONS,
    get_file_size_bits,
    get_file_size_bytes,
    leer_texto_con_encoding,
    save_text_file,
)
from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.metrics import measure_algorithm, summarize_result
from experiments.benchmark import run_benchmark, print_benchmark_table


def format_bytes(n_bytes: int) -> str:
    """Formatea bytes insertando comas para miles."""
    return f"{n_bytes:,}"


def format_bits(n_bits: int) -> str:
    """Formatea bits insertando comas para miles."""
    return f"{n_bits:,}"


def print_loaded_file_info(path: str, text: str, encoding: str) -> None:
    """Muestra estadísticas reales del archivo y del texto leído."""
    file_bytes = get_file_size_bytes(path)
    file_bits = file_bytes * 8
    logical_bytes = len(text.encode(encoding))
    logical_bits = logical_bytes * 8

    # Estadísticas de caracteres
    total_caracteres = len(text)
    caracteres_sin_espacios = len(
        text.replace(" ", "")
            .replace("\n", "")
            .replace("\r", "")
            .replace("\t", "")
    )
    palabras = len(text.split())
    lineas = text.count("\n") + 1 if text else 0

    print("\nArchivo cargado correctamente.")
    print(f"- Ruta: {path}")
    print(f"- Codificación usada: {encoding}")
    print(f"- Caracteres totales: {total_caracteres:,}")
    print(f"- Caracteres sin espacios ni saltos de línea: {caracteres_sin_espacios:,}")
    print(f"- Palabras: {palabras:,}")
    print(f"- Líneas: {lineas:,}")
    print(f"Tamaño real del archivo original: {format_bytes(file_bytes)} bytes")
    print(f"Tamaño real del archivo original: {format_bits(file_bits)} bits")
    print(f"Tamaño lógico del texto leído: {format_bytes(logical_bytes)} bytes")
    print(f"Tamaño lógico del texto leído: {format_bits(logical_bits)} bits")

    if file_bits == logical_bits:
        print("- Verificación de tamaño: coincide con el archivo original.")
    else:
        print(
            "- Verificación de tamaño: no coincide exactamente. "
            "Esto puede ocurrir por codificación (BOM), saltos de línea (CRLF/LF) o caracteres especiales."
        )


def print_reporte_completo(result: dict, orig_path: str, comp_path: str, dec_path: str) -> None:
    """Imprime el reporte detallado con el formato exacto requerido por el usuario."""
    texto = result["decompressed_text"]
    total_caracteres = len(texto)
    caracteres_sin_espacios = len(
        texto.replace(" ", "")
             .replace("\n", "")
             .replace("\r", "")
             .replace("\t", "")
    )
    palabras = len(texto.split())
    lineas = texto.count("\n") + 1 if texto else 0

    orig_bytes = result["original_size_bytes"]
    orig_bits = result["original_size_bits"]
    
    logical_bytes = result["logical_original_size_bytes"]
    logical_bits = result["logical_original_size_bits"]
    
    comp_bytes = result["compressed_size_bytes"]
    comp_bits = result["compressed_size_bits"]
    
    dec_bytes = result["decompressed_size_bytes"]
    dec_bits = result["decompressed_size_bits"]
    
    encoding = result["encoding_used"]
    lossless_str = "OK" if result["lossless"] else "ERROR"
    diff_bytes = dec_bytes - orig_bytes
    lossless_bool_str = "SÍ" if result["lossless"] else "NO"
    
    ratio = result["compression_ratio"]
    pct_comprimido = result["porcentaje_comprimido"]
    ahorro = result["reduction_percentage"]
    
    orig_name = Path(orig_path).name
    orig_ext = Path(orig_path).suffix

    print("\n========================================")
    print("REPORTE DE TEXTZIPLAB")
    print("========================================")
    print("")
    print("ARCHIVO ORIGINAL")
    print(f"- Ruta: {orig_path}")
    print(f"- Nombre: {orig_name}")
    print(f"- Extensión: {orig_ext}")
    print(f"- Tamaño real: {format_bytes(orig_bytes)} bytes")
    print(f"- Tamaño real: {format_bits(orig_bits)} bits")
    print("")
    print("TEXTO LEÍDO")
    print(f"- Codificación usada: {encoding}")
    print(f"- Caracteres totales: {total_caracteres:,}")
    print(f"- Caracteres sin espacios ni saltos de línea: {caracteres_sin_espacios:,}")
    print(f"- Palabras: {palabras:,}")
    print(f"- Líneas: {lineas:,}")
    print(f"- Tamaño lógico del texto leído: {format_bytes(logical_bytes)} bytes")
    print(f"- Tamaño lógico del texto leído: {format_bits(logical_bits)} bits")
    print("")
    print("ARCHIVO COMPRIMIDO")
    print(f"- Ruta: {comp_path}")
    print(f"- Tamaño real: {format_bytes(comp_bytes)} bytes")
    print(f"- Tamaño real: {format_bits(comp_bits)} bits")
    print("")
    print("ARCHIVO DESCOMPRIMIDO")
    print(f"- Ruta: {dec_path}")
    print(f"- Tamaño real: {format_bytes(dec_bytes)} bytes")
    print(f"- Tamaño real: {format_bits(dec_bits)} bits")
    print("")
    print("VALIDACIÓN")
    print(f"- Original vs descomprimido byte a byte: {lossless_str}")
    print(f"- Diferencia de bytes: {diff_bytes:,}")
    print(f"- ¿Compresión sin pérdida?: {lossless_bool_str}")
    print("")
    print("RESULTADOS DE COMPRESIÓN")
    print(f"- Ratio de compresión: {ratio:.4f}")
    print(f"- Porcentaje comprimido respecto al original: {pct_comprimido:.2f}%")
    print(f"- Ahorro de espacio: {ahorro:.2f}%")
    print("")
    print("OBSERVACIÓN")
    print("- El tamaño lógico del texto puede diferir del tamaño físico del archivo por codificación, saltos de línea o caracteres especiales.")
    print("- La métrica principal de compresión compara el tamaño físico del archivo original contra el tamaño físico del archivo comprimido.")
    print("========================================")


def get_default_paths(current_file_path: str | None, current_text: str, algo_name: str) -> tuple[str, str, str]:
    """Genera rutas de guardado por defecto en base al archivo abierto o texto manual."""
    if current_file_path:
        orig_path = current_file_path
        ext = Path(current_file_path).suffix
        comp_path = current_file_path + ("_comp.huff" if algo_name == "Huffman" else "_comp.lzw")
        dec_path = current_file_path + f"_dec_{algo_name}{ext}"
    else:
        Path("temp_run").mkdir(parents=True, exist_ok=True)
        orig_path = "temp_run/manual_input.txt"
        save_text_file(orig_path, current_text, encoding="utf-8")
        comp_path = f"temp_run/manual_input_comp.{algo_name.lower()}"
        dec_path = f"temp_run/manual_input_dec_{algo_name}.txt"
    return orig_path, comp_path, dec_path


def export_last_results(results: list[dict], path: str = "experiments/results/manual_results.csv") -> None:
    """Exporta los últimos resultados de métricas a un CSV."""
    if not results:
        print("No hay resultados para exportar.")
        return

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([summarize_result(row) for row in results])
    df.to_csv(output, index=False, encoding="utf-8")
    print(f"Resultados exportados a: {output}")


def run_cli() -> None:
    """Bucle principal de la interfaz por consola."""
    current_text = ""
    current_file_path: str | None = None
    current_encoding: str = "utf-8"
    last_results: list[dict] = []

    while True:
        print("\n=== TextZipLab - Consola ===")
        print("1. Cargar texto manual")
        print("2. Cargar archivo textual")
        print("3. Comprimir con Huffman")
        print("4. Comprimir con LZW")
        print("5. Comparar Huffman vs LZW")
        print("6. Ejecutar benchmark experimental")
        print("7. Exportar resultados")
        print("8. Salir")

        option = input("Seleccione una opción: ").strip()

        try:
            if option == "1":
                print("Ingrese el texto. Finalice con una línea vacía:")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                current_text = "\n".join(lines)
                current_file_path = None
                current_encoding = "utf-8"
                print(f"Texto cargado: {len(current_text)} caracteres")
                print(f"Tamaño lógico del texto: {len(current_text.encode('utf-8')) * 8} bits")

            elif option == "2":
                allowed = ", ".join(sorted(TEXT_EXTENSIONS))
                print(f"Formatos permitidos: {allowed}")
                path = input("Ruta del archivo textual: ").strip().strip('"')
                try:
                    current_text, current_encoding = leer_texto_con_encoding(path)
                    current_file_path = path
                    print_loaded_file_info(path, current_text, current_encoding)
                except ValueError as error:
                    print(f"\nError: {error}")
                except Exception as error:
                    print(f"\nError al cargar el archivo: {error}")

            elif option == "3":
                if current_text == "":
                    print("Primero cargue un texto.")
                    continue
                orig_path, comp_path, dec_path = get_default_paths(current_file_path, current_text, "Huffman")
                result = measure_algorithm(
                    HuffmanCompressor(),
                    current_text,
                    source_file_path=current_file_path,
                    compressed_path=comp_path,
                    decompressed_path=dec_path,
                )
                print_reporte_completo(result, orig_path, comp_path, dec_path)
                last_results = [result]

            elif option == "4":
                if current_text == "":
                    print("Primero cargue un texto.")
                    continue
                orig_path, comp_path, dec_path = get_default_paths(current_file_path, current_text, "LZW")
                result = measure_algorithm(
                    LZWCompressor(),
                    current_text,
                    source_file_path=current_file_path,
                    compressed_path=comp_path,
                    decompressed_path=dec_path,
                )
                print_reporte_completo(result, orig_path, comp_path, dec_path)
                last_results = [result]

            elif option == "5":
                if current_text == "":
                    print("Primero cargue un texto.")
                    continue
                print(f"\nTexto analizado: {current_text[:120]}{'...' if len(current_text) > 120 else ''}")
                
                h_orig, h_comp, h_dec = get_default_paths(current_file_path, current_text, "Huffman")
                h_result = measure_algorithm(
                    HuffmanCompressor(),
                    current_text,
                    source_file_path=current_file_path,
                    compressed_path=h_comp,
                    decompressed_path=h_dec,
                )

                l_orig, l_comp, l_dec = get_default_paths(current_file_path, current_text, "LZW")
                l_result = measure_algorithm(
                    LZWCompressor(),
                    current_text,
                    source_file_path=current_file_path,
                    compressed_path=l_comp,
                    decompressed_path=l_dec,
                )

                print("\n=== COMPARACIÓN DE ALGORITMOS ===")
                print_reporte_completo(h_result, h_orig, h_comp, h_dec)
                print_reporte_completo(l_result, l_orig, l_comp, l_dec)

                last_results = [h_result, l_result]
                best_reduction = max(last_results, key=lambda item: item["reduction_percentage"])
                fastest = min(last_results, key=lambda item: item["total_time_seconds"])

                print("\nConclusión automática:")
                print(f"Para este caso, el algoritmo con mejor reducción fue {best_reduction['algorithm']}.")
                print(f"El algoritmo con menor tiempo fue {fastest['algorithm']}.")

                table = pd.DataFrame([summarize_result(row) for row in last_results])
                print("\nTabla comparativa:")
                print(table.to_string(index=False))

            elif option == "6":
                include_large = input("¿Incluir casos grandes de 10^6 caracteres? (s/N): ").strip().lower() == "s"
                df = run_benchmark(include_large=include_large)
                print_benchmark_table(df)
                print("\nCSV generado en experiments/results/results.csv")

            elif option == "7":
                export_last_results(last_results)

            elif option == "8":
                print("Saliendo de TextZipLab.")
                break

            else:
                print("Opción inválida.")

        except Exception as error:
            print(f"Error: {error}")


def main() -> None:
    # Si se pasa --gui como argumento por línea de comandos, se lanza directo la GUI
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        from gui.main_window import run_gui
        run_gui()
        return

    # De lo contrario, preguntar al usuario
    print("=== TextZipLab ===")
    print("1. Ejecutar en Consola (CLI)")
    print("2. Ejecutar Interfaz Gráfica (GUI - PySide6)")
    start_opt = input("Seleccione una opción: ").strip()

    if start_opt == "2":
        try:
            from gui.main_window import run_gui
            run_gui()
        except Exception as error:
            print(f"No se pudo iniciar la interfaz gráfica: {error}")
            print("Iniciando modo consola por defecto...")
            run_cli()
    else:
        run_cli()


if __name__ == "__main__":
    main()
