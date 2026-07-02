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
    save_compressed_file,
    load_compressed_file,
    preview_compressed_data,
    validate_compressed_data,
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
    
    # Métricas lógicas
    logical_comp_bits = result.get("logical_compressed_size_bits", 0)
    logical_comp_bytes = result.get("logical_compressed_size_bytes", 0)
    logical_ratio = result.get("logical_compression_ratio", 0.0)
    logical_ahorro = result.get("logical_reduction_percentage", 0.0)
    
    # Métricas físicas
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
    print(f"- Tamaño físico real: {format_bytes(orig_bytes)} bytes ({format_bits(orig_bits)} bits)")
    print("")
    print("TEXTO LEÍDO")
    print(f"- Codificación usada: {encoding}")
    print(f"- Caracteres totales: {total_caracteres:,}")
    print(f"- Caracteres sin espacios ni saltos de línea: {caracteres_sin_espacios:,}")
    print(f"- Palabras: {palabras:,}")
    print(f"- Líneas: {lineas:,}")
    print(f"- Tamaño lógico del texto leído: {format_bytes(logical_bytes)} bytes ({format_bits(logical_bits)} bits)")
    print("")
    print("ARCHIVO COMPRIMIDO GUARDADO (FÍSICO EN DISCO)")
    print(f"- Ruta: {comp_path}")
    print(f"- Tamaño físico real en disco: {format_bytes(comp_bytes)} bytes ({format_bits(comp_bits)} bits)")
    print("")
    print("COMPRESIÓN LÓGICA (TEÓRICA - BITSTREAM)")
    print(f"- Tamaño lógico comprimido: {format_bytes(logical_comp_bytes)} bytes ({format_bits(logical_comp_bits)} bits)")
    print("")
    print("ARCHIVO DESCOMPRIMIDO")
    print(f"- Ruta: {dec_path}")
    print(f"- Tamaño real: {format_bytes(dec_bytes)} bytes ({format_bits(dec_bits)} bits)")
    print("")
    print("VALIDACIÓN")
    print(f"- Original vs descomprimido byte a byte: {lossless_str}")
    print(f"- Diferencia de bytes: {diff_bytes:,}")
    print(f"- ¿Compresión sin pérdida?: {lossless_bool_str}")
    print("")
    print("RESULTADOS DE COMPRESIÓN")
    print("  [Métricas Lógicas / Teóricas]:")
    print(f"  - Ratio lógico: {logical_ratio:.4f}")
    print(f"  - Ahorro lógico: {logical_ahorro:.2f}%")
    print("  [Métricas Físicas / En disco real]:")
    print(f"  - Ratio físico: {ratio:.4f}")
    print(f"  - Porcentaje comprimido: {pct_comprimido:.2f}%")
    print(f"  - Ahorro físico real: {ahorro:.2f}%")
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
    loaded_compressed_data: dict | None = None
    loaded_compressed_path: str | None = None

    while True:
        print("\n=== TextZipLab - Consola ===")
        print("1. Cargar texto manual")
        print("2. Cargar archivo textual")
        print("3. Comprimir con Huffman")
        print("4. Comprimir con LZW")
        print("5. Comparar Huffman vs LZW")
        print("6. Ejecutar benchmark experimental")
        print("7. Exportar resultados")
        print("8. Guardar comprimido real (.huff / .lzw)")
        print("9. Cargar comprimido real o JSON")
        print("10. Descomprimir comprimido")
        print("11. Exportar vista académica JSON (.json)")
        print("12. Comparar peso original vs comprimido guardado")
        print("13. Salir")

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
                if not last_results:
                    print("Primero realice una compresión (opciones 3, 4 o 5).")
                    continue
                compressed_data = last_results[-1]["compressed_data"]
                algo = compressed_data.get("algorithm")
                
                # Inyectar extensión y codificación original
                orig_file = current_file_path if current_file_path else "temp_run/manual_input.txt"
                compressed_data["original_extension"] = Path(orig_file).suffix
                compressed_data["original_encoding"] = current_encoding
                
                ext = ".huff" if algo == "Huffman" else ".lzw"
                if current_file_path:
                    default_path = current_file_path + ext
                else:
                    default_path = "temp_run/manual_input" + ext
                
                path = input(f"Ruta de destino [{default_path}]: ").strip().strip('"')
                if not path:
                    path = default_path
                
                save_compressed_file(path, compressed_data)
                file_size_bytes = get_file_size_bytes(path)
                print(f"\nArchivo comprimido REAL guardado correctamente en: {path}")
                print(f"Tamaño físico real del archivo guardado: {format_bytes(file_size_bytes)} bytes ({format_bits(file_size_bytes * 8)} bits)")

            elif option == "9":
                path = input("Ruta del archivo comprimido (.huff / .lzw / .json): ").strip().strip('"')
                try:
                    loaded_compressed_data = load_compressed_file(path)
                    loaded_compressed_path = path
                    print(f"\nArchivo cargado correctamente: {path}")
                    print(f"Algoritmo detectado: {loaded_compressed_data.get('algorithm')}")
                    print(f"Extensión original recuperada de cabecera: {loaded_compressed_data.get('original_extension', '.txt')}")
                    print(f"Codificación original recuperada de cabecera: {loaded_compressed_data.get('original_encoding', 'utf-8')}")
                except Exception as error:
                    print(f"\nError al cargar el archivo: {error}")

            elif option == "10":
                if loaded_compressed_data is None:
                    print("Primero cargue un archivo comprimido (opción 9).")
                    continue
                algo = loaded_compressed_data.get("algorithm")
                try:
                    if algo == "Huffman":
                        compressor = HuffmanCompressor()
                    elif algo == "LZW":
                        compressor = LZWCompressor()
                    else:
                        raise ValueError(f"Algoritmo desconocido: {algo}")
                    
                    decompressed_text = compressor.decompress(loaded_compressed_data)
                    print(f"\nDescompresión exitosa utilizando {algo}.")
                    
                    # Calcular tamaño del texto recuperado
                    orig_enc = loaded_compressed_data.get("original_encoding")
                    if orig_enc is None:
                        orig_enc = "utf-8"
                    
                    rec_bytes = len(decompressed_text.encode(orig_enc))
                    rec_bits = rec_bytes * 8
                    
                    print(f"Ruta del archivo comprimido cargado: {loaded_compressed_path}")
                    comp_physical_bytes = get_file_size_bytes(loaded_compressed_path) if loaded_compressed_path else 0
                    print(f"Tamaño físico del comprimido en disco: {format_bytes(comp_physical_bytes)} bytes ({format_bits(comp_physical_bytes * 8)} bits)")
                    print(f"Tamaño del texto recuperado: {format_bytes(rec_bytes)} bytes ({format_bits(rec_bits)} bits)")
                    print(f"Cantidad de caracteres recuperados: {len(decompressed_text):,}")
                    
                    # Vista previa ampliada de hasta 5,000 caracteres
                    lim = 5000
                    preview_text = decompressed_text[:lim]
                    print(f"\n=== VISTA PREVIA DEL CONTENIDO RECUPERADO ({'PARCIAL' if len(decompressed_text) > lim else 'COMPLETO'}) ===")
                    print(preview_text)
                    if len(decompressed_text) > lim:
                        print(f"... [Mostrando primeros 5,000 caracteres de {len(decompressed_text):,} totales] ...")
                    print("=====================================================================")
                    
                    save_opt = input("¿Desea guardar el texto recuperado en un archivo? (s/N): ").strip().lower()
                    if save_opt == "s":
                        orig_ext = loaded_compressed_data.get("original_extension")
                        if orig_ext is None:
                            orig_ext = ".txt"
                        orig_name = loaded_compressed_data.get("original_name")
                        if orig_name:
                            orig_name_stem = Path(orig_name).stem
                            default_rec = f"temp_run/{orig_name_stem}_recuperado{orig_ext}"
                        else:
                            default_rec = f"temp_run/archivo_recuperado{orig_ext}"
                        
                        save_path = input(f"Ruta de destino [{default_rec}]: ").strip().strip('"')
                        if not save_path:
                            save_path = default_rec
                        save_text_file(save_path, decompressed_text, encoding=orig_enc)
                        print(f"Texto recuperado guardado en: {save_path} con codificación {orig_enc}")
                except Exception as error:
                    print(f"\nError al descomprimir: {error}")

            elif option == "11":
                if not last_results:
                    print("Primero realice una compresión (opciones 3, 4 o 5).")
                    continue
                compressed_data = last_results[-1]["compressed_data"]
                algo = compressed_data.get("algorithm")
                
                # Inyectar extensión y codificación original
                orig_file = current_file_path if current_file_path else "temp_run/manual_input.txt"
                compressed_data["original_extension"] = Path(orig_file).suffix
                compressed_data["original_encoding"] = current_encoding
                compressed_data["original_name"] = Path(orig_file).name
                compressed_data["original_size_bytes"] = get_file_size_bytes(orig_file)
                
                ext = ".huff.json" if algo == "Huffman" else ".lzw.json"
                if current_file_path:
                    default_path = current_file_path + ext
                else:
                    default_path = "temp_run/manual_input" + ext
                
                path = input(f"Ruta de destino [{default_path}]: ").strip().strip('"')
                if not path:
                    path = default_path
                
                save_compressed_file(path, compressed_data)
                file_size_bytes = get_file_size_bytes(path)
                print(f"\nVista académica JSON exportada correctamente en: {path}")
                print(f"Tamaño físico del JSON: {format_bytes(file_size_bytes)} bytes")
                print("* Aclaración Académica: El archivo JSON contiene metadatos estructurados legibles, por lo que pesa más que el bitstream comprimido real.")

            elif option == "12":
                if loaded_compressed_data is None:
                    print("Primero cargue un archivo comprimido (opción 9).")
                    continue
                if loaded_compressed_path is None:
                    print("No se encuentra la ruta del archivo comprimido.")
                    continue
                
                orig_bytes = loaded_compressed_data.get("original_size_bytes")
                comp_bits_theoretical = loaded_compressed_data.get("compressed_size_bits")
                
                json_bytes = get_file_size_bytes(loaded_compressed_path)
                json_bits = json_bytes * 8
                
                is_json = loaded_compressed_path.lower().endswith(".json")
                
                print("\n=== COMPARATIVA DE PESOS ===")
                
                if orig_bytes is not None:
                    orig_bits = orig_bytes * 8
                    print(f"ARCHIVO ORIGINAL:")
                    print(f"- Tamaño físico original: {format_bytes(orig_bytes)} bytes ({format_bits(orig_bits)} bits)")
                else:
                    print(f"ARCHIVO ORIGINAL:")
                    print(f"- Tamaño físico original: No disponible (archivo heredado sin metadatos)")
                    
                if comp_bits_theoretical is not None:
                    comp_bytes_theoretical = (comp_bits_theoretical + 7) // 8
                    print(f"COMPRESIÓN LÓGICA (Teórica / Bitstream del algoritmo):")
                    print(f"- Tamaño lógico/teórico: {format_bytes(comp_bytes_theoretical)} bytes ({format_bits(comp_bits_theoretical)} bits)")
                    if orig_bytes is not None and orig_bytes > 0:
                        ratio_theoretical = comp_bits_theoretical / (orig_bytes * 8)
                        pct_theoretical = (1.0 - ratio_theoretical) * 100
                        print(f"- Ratio teórico: {ratio_theoretical:.4f}")
                        print(f"- Ahorro teórico de espacio: {pct_theoretical:.2f}%")
                    else:
                        print(f"- Ratio teórico: No disponible")
                        print(f"- Ahorro teórico de espacio: No disponible")
                else:
                    print(f"COMPRESIÓN LÓGICA (Teórica / Bitstream del algoritmo):")
                    print(f"- Tamaño lógico/teórico: No disponible")
                    print(f"- Ratio teórico: No disponible")
                    print(f"- Ahorro teórico de espacio: No disponible")
                
                if is_json:
                    print(f"ARCHIVO COMPRIMIDO GUARDADO EN DISCO (JSON académico):")
                else:
                    print(f"ARCHIVO COMPRIMIDO GUARDADO EN DISCO (Binario Real):")
                print(f"- Tamaño físico real en disco: {format_bytes(json_bytes)} bytes ({format_bits(json_bits)} bits)")
                
                if orig_bytes is not None and orig_bytes > 0:
                    ratio_json = json_bytes / orig_bytes
                    pct_json = (1.0 - ratio_json) * 100
                    print(f"- Ratio real: {ratio_json:.4f}")
                    print(f"- Ahorro real de espacio: {pct_json:.2f}%")
                else:
                    print(f"- Ratio real: No disponible")
                    print(f"- Ahorro real de espacio: No disponible")
                
                if is_json:
                    print("\n* Aclaración Académica: El archivo JSON físico guardado en disco pesa más que el tamaño comprimido lógico/teórico del algoritmo. Esto ocurre porque el archivo JSON es en formato de texto plano y contiene metadatos legibles (como el diccionario de frecuencias de caracteres o alfabeto de entrada) necesarios para que la descompresión posterior sea posible de forma autónoma.")
                else:
                    print("\n* Nota: El archivo binario guardado en disco tiene un tamaño muy similar al bitstream teórico debido a que las cabeceras personalizadas de metadatos ('TZHUF1' o 'TZLZW1') tienen un peso mínimo en disco.")

            elif option == "13":
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
