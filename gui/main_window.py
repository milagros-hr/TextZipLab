"""Interfaz gráfica PySide6 para TextZipLab."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.file_manager import (
    TEXT_EXTENSIONS,
    get_file_size_bytes,
    leer_texto_con_encoding,
    save_text_file,
)
from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.metrics import measure_algorithm, summarize_result
from experiments.benchmark import run_benchmark


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextZipLab - Analizador y Compresor Multiformato")
        self.resize(1100, 750)

        # Variables de estado
        self.current_text: str = ""
        self.current_file_path: str | None = None
        self.current_encoding: str = "utf-8"
        self.last_results: list[dict[str, Any]] = []

        # Cargar estilos
        self.load_stylesheet()

        # Construir UI
        self.init_ui()

    def load_stylesheet(self) -> None:
        """Carga el archivo QSS de estilos."""
        qss_path = Path(__file__).parent / "styles.qss"
        if qss_path.exists():
            try:
                self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Error al cargar la hoja de estilos: {e}")

    def init_ui(self) -> None:
        # Widget y Layout principal
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ------------------ PANEL IZQUIERDO (CONTROLES) ------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Grupo: Carga de Archivo
        load_group = QGroupBox("Cargar Archivo de Texto")
        load_layout = QVBoxLayout(load_group)
        load_layout.setSpacing(10)

        self.load_button = QPushButton("Seleccionar archivo")
        self.load_button.setObjectName("load_button")
        self.load_button.clicked.connect(self.select_file)
        load_layout.addWidget(self.load_button)

        self.file_info_label = QLabel("Ningún archivo cargado.")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setStyleSheet("color: #a1a1aa;")
        load_layout.addWidget(self.file_info_label)
        
        left_layout.addWidget(load_group)

        # Grupo: Operaciones de Compresión
        ops_group = QGroupBox("Algoritmos y Operaciones")
        ops_layout = QVBoxLayout(ops_group)
        ops_layout.setSpacing(12)

        ops_layout.addWidget(QLabel("Seleccionar algoritmo principal:"))
        self.algo_selector = QComboBox()
        self.algo_selector.addItems(["Huffman", "LZW"])
        ops_layout.addWidget(self.algo_selector)

        self.compress_button = QPushButton("Comprimir")
        self.compress_button.clicked.connect(self.run_compression)
        self.compress_button.setEnabled(False)
        ops_layout.addWidget(self.compress_button)

        self.decompress_button = QPushButton("Descomprimir")
        self.decompress_button.clicked.connect(self.run_decompression)
        self.decompress_button.setEnabled(False)
        ops_layout.addWidget(self.decompress_button)

        self.compare_button = QPushButton("Comparar ambos algoritmos")
        self.compare_button.setObjectName("compare_button")
        self.compare_button.clicked.connect(self.compare_algorithms)
        self.compare_button.setEnabled(False)
        ops_layout.addWidget(self.compare_button)

        self.benchmark_button = QPushButton("Ejecutar benchmark académico")
        self.benchmark_button.clicked.connect(self.run_academic_benchmark)
        ops_layout.addWidget(self.benchmark_button)

        left_layout.addWidget(ops_group)
        left_layout.addStretch()

        left_panel.setFixedWidth(280)
        main_layout.addWidget(left_panel)

        # ------------------ PANEL DERECHO (RESULTADOS) ------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Área de Reporte de Texto
        right_layout.addWidget(QLabel("<b>Reporte de Resultados</b>"))
        self.report_area = QTextEdit()
        self.report_area.setReadOnly(True)
        self.report_area.setPlaceholderText("Los reportes detallados y la información de validación aparecerán aquí...")
        right_layout.addWidget(self.report_area, stretch=3)

        # Tabla Comparativa
        right_layout.addWidget(QLabel("<b>Tabla Comparativa</b>"))
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Algoritmo",
            "Tam. Original",
            "Tam. Comprimido",
            "Ratio",
            "Ahorro",
            "T. Compresión",
            "T. Descompresión",
            "Validación"
        ])
        
        # Ajustar headers de tabla
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.results_table, stretch=2)

        main_layout.addWidget(right_panel)

        self.setCentralWidget(main_widget)
        self.statusBar().showMessage("Listo")

    def select_file(self) -> None:
        """Abre un diálogo de archivo y valida la selección del usuario."""
        allowed_filters = (
            "Archivos de texto (*.txt *.csv *.json *.xml *.html *.htm *.css *.js *.py *.java *.cpp *.c *.md *.log *.ini *.cfg *.yaml *.yml *.sql);;"
            "Todos los archivos (*.*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de texto", "", allowed_filters)
        
        if not file_path:
            return

        try:
            # Leer el archivo con detección robusta de codificación
            text, enc = leer_texto_con_encoding(file_path)
            self.current_text = text
            self.current_file_path = file_path
            self.current_encoding = enc

            # Mostrar información del archivo cargado
            name = Path(file_path).name
            size = get_file_size_bytes(file_path)
            
            # Estadísticas adicionales
            total_chars = len(text)
            words = len(text.split())
            lines = text.count("\n") + 1 if text else 0

            self.file_info_label.setText(
                f"<b>Archivo:</b> {name}<br>"
                f"<b>Tamaño:</b> {size:,} bytes ({size*8:,} bits)<br>"
                f"<b>Codificación:</b> {enc}<br>"
                f"<b>Caracteres:</b> {total_chars:,}<br>"
                f"<b>Palabras:</b> {words:,}<br>"
                f"<b>Líneas:</b> {lines:,}"
            )
            
            # Limpiar reportes previos
            self.report_area.clear()
            self.results_table.setRowCount(0)
            self.last_results.clear()

            # Habilitar botones de acción
            self.compress_button.setEnabled(True)
            self.decompress_button.setEnabled(False)
            self.compare_button.setEnabled(True)
            self.statusBar().showMessage(f"Archivo cargado con éxito: {name}")

        except ValueError as e:
            QMessageBox.critical(self, "Archivo No Permitido", str(e))
            self.statusBar().showMessage("Error: archivo no permitido.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Lectura", f"No se pudo cargar el archivo:\n{e}")
            self.statusBar().showMessage("Error al abrir el archivo.")

    def run_compression(self) -> None:
        """Ejecuta la compresión con el algoritmo seleccionado."""
        if not self.current_text:
            QMessageBox.warning(self, "Sin contenido", "Por favor, cargue un archivo de texto primero.")
            return

        algo = self.algo_selector.currentText()
        compressor = HuffmanCompressor() if algo == "Huffman" else LZWCompressor()

        # Determinar rutas
        orig_path, comp_path, dec_path = self.get_paths(algo)

        try:
            self.statusBar().showMessage(f"Comprimiendo con {algo}...")
            QApplication.processEvents()

            result = measure_algorithm(
                compressor,
                self.current_text,
                source_file_path=self.current_file_path,
                compressed_path=comp_path,
                decompressed_path=dec_path
            )

            # Generar reporte textual
            report = self.generate_report_string(result, orig_path, comp_path, dec_path)
            self.report_area.setText(report)

            # Agregar a la tabla de resultados
            self.add_to_table(result)
            self.last_results.append(result)

            # Habilitar descompresión
            self.decompress_button.setEnabled(True)
            self.statusBar().showMessage(f"Compresión con {algo} completada.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Compresión", f"Se produjo un error durante la compresión:\n{e}")
            self.statusBar().showMessage("Error al comprimir.")

    def run_decompression(self) -> None:
        """Verifica y ejecuta la descompresión a partir del archivo comprimido físico."""
        if not self.last_results:
            QMessageBox.warning(self, "Sin datos", "No hay datos comprimidos recientes para descomprimir.")
            return

        last_result = self.last_results[-1]
        algo = last_result["algorithm"]
        _, comp_path, dec_path = self.get_paths(algo)

        if not Path(comp_path).exists():
            QMessageBox.critical(self, "Archivo faltante", f"No se encontró el archivo comprimido en:\n{comp_path}")
            return

        try:
            self.statusBar().showMessage(f"Descomprimiendo desde {comp_path}...")
            QApplication.processEvents()

            # El método measure_algorithm ya corrió la descompresión y guardó en dec_path,
            # pero simulamos la lectura física del archivo y validación por separado
            # para demostrar que funciona independientemente.
            from core.file_manager import load_compressed_file, save_text_file
            from core.validator import comparar_archivos_byte_a_byte
            
            # Cargar
            compressed_data = load_compressed_file(comp_path)
            compressor = HuffmanCompressor() if algo == "Huffman" else LZWCompressor()
            
            # Descomprimir
            decompressed_text = compressor.decompress(compressed_data)
            
            # Guardar
            save_text_file(dec_path, decompressed_text, encoding=last_result["encoding_used"])
            
            # Validar byte a byte
            orig_path = self.current_file_path if self.current_file_path else "temp_run/manual_input.txt"
            lossless = comparar_archivos_byte_a_byte(orig_path, dec_path)

            if lossless:
                QMessageBox.information(
                    self,
                    "Descompresión Exitosa",
                    f"El archivo se descomprimió correctamente en:\n{dec_path}\n\n"
                    f"¡Validación byte a byte: OK (Idéntico al original)!"
                )
                self.statusBar().showMessage("Descompresión e integridad validadas: OK.")
            else:
                QMessageBox.warning(
                    self,
                    "Error de Integridad",
                    f"El archivo se descomprimió pero NO es idéntico al original.\n"
                    f"¡Validación byte a byte: ERROR (Pérdida de datos)!"
                )
                self.statusBar().showMessage("Error: fallo de integridad en descompresión.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Descompresión", f"No se pudo descomprimir el archivo:\n{e}")
            self.statusBar().showMessage("Error al descomprimir.")

    def compare_algorithms(self) -> None:
        """Comprime el texto con Huffman y LZW para mostrar una comparación directa."""
        if not self.current_text:
            return

        try:
            self.statusBar().showMessage("Comparando Huffman vs LZW...")
            QApplication.processEvents()

            # Huffman
            h_orig, h_comp, h_dec = self.get_paths("Huffman")
            h_result = measure_algorithm(
                HuffmanCompressor(),
                self.current_text,
                source_file_path=self.current_file_path,
                compressed_path=h_comp,
                decompressed_path=h_dec
            )

            # LZW
            l_orig, l_comp, l_dec = self.get_paths("LZW")
            l_result = measure_algorithm(
                LZWCompressor(),
                self.current_text,
                source_file_path=self.current_file_path,
                compressed_path=l_comp,
                decompressed_path=l_dec
            )

            # Generar reportes combinados
            h_report = self.generate_report_string(h_result, h_orig, h_comp, h_dec)
            l_report = self.generate_report_string(l_result, l_orig, l_comp, l_dec)

            comparison_text = (
                "============================================================\n"
                "           COMPARATIVA DIRECTA: HUFFMAN VS LZW\n"
                "============================================================\n\n"
                f"{h_report}\n\n"
                "------------------------------------------------------------\n\n"
                f"{l_report}\n\n"
                "============================================================\n"
                "CONCLUSIÓN AUTOMÁTICA\n"
                "============================================================\n"
            )

            # Agregar conclusión
            best_reduction = max([h_result, l_result], key=lambda item: item["reduction_percentage"])
            fastest = min([h_result, l_result], key=lambda item: item["total_time_seconds"])

            comparison_text += (
                f"- Mejor reducción de espacio: {best_reduction['algorithm']} "
                f"({best_reduction['reduction_percentage']:.2f}% de ahorro)\n"
                f"- Mayor velocidad de procesamiento: {fastest['algorithm']} "
                f"({fastest['total_time_seconds']:.6f} segundos totales)\n"
            )

            self.report_area.setText(comparison_text)

            # Actualizar tabla
            self.results_table.setRowCount(0)
            self.add_to_table(h_result)
            self.add_to_table(l_result)

            self.last_results = [h_result, l_result]
            self.decompress_button.setEnabled(True)
            self.statusBar().showMessage("Comparación finalizada.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Comparación", f"No se pudo completar la comparación:\n{e}")
            self.statusBar().showMessage("Error al comparar.")

    def run_academic_benchmark(self) -> None:
        """Ejecuta el benchmark experimental estándar y muestra la tabla."""
        self.statusBar().showMessage("Ejecutando benchmark académico en segundo plano...")
        QApplication.processEvents()
        
        try:
            # Ejecutar benchmark básico (sin casos gigantes por rapidez en GUI)
            df = run_benchmark(include_large=False)
            
            # Limpiar interfaz
            self.results_table.setRowCount(0)
            self.report_area.clear()
            
            self.report_area.append("============================================================\n")
            self.report_area.append("          BENCHMARK EXPERIMENTAL COMPLETADO\n")
            self.report_area.append("============================================================\n\n")
            self.report_area.append(f"Resultados guardados en: experiments/results/results.csv\n\n")
            
            # Agrupar y formatear los resultados
            self.report_area.append(df.to_string(index=False))
            
            # Rellenar la tabla con los resultados del benchmark
            for _, row in df.iterrows():
                # Saltar filas teóricas
                if row.get("algorithm") == "Teorico":
                    continue
                
                row_idx = self.results_table.rowCount()
                self.results_table.insertRow(row_idx)
                
                # Campos resumidos
                self.results_table.setItem(row_idx, 0, QTableWidgetItem(f"{row['case_name']} ({row['algorithm']})"))
                
                orig_bits = row.get("original_size_bits", 0)
                comp_bits = row.get("compressed_size_bits", 0)
                orig_bytes = orig_bits // 8
                comp_bytes = comp_bits // 8
                
                self.results_table.setItem(row_idx, 1, QTableWidgetItem(f"{orig_bytes:,} bytes"))
                self.results_table.setItem(row_idx, 2, QTableWidgetItem(f"{comp_bytes:,} bytes"))
                
                ratio = row.get("compression_ratio", 0)
                ahorro = row.get("reduction_percentage", 0)
                self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{ratio:.4f}"))
                self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{ahorro:.2f}%"))
                
                t_comp = row.get("compression_time_seconds", 0)
                t_dec = row.get("decompression_time_seconds", 0)
                self.results_table.setItem(row_idx, 5, QTableWidgetItem(f"{t_comp:.6f} s"))
                self.results_table.setItem(row_idx, 6, QTableWidgetItem(f"{t_dec:.6f} s"))
                
                lossless = row.get("lossless", False)
                self.results_table.setItem(row_idx, 7, QTableWidgetItem("OK" if lossless else "ERROR"))
            
            self.statusBar().showMessage("Benchmark académico finalizado.")

        except Exception as e:
            QMessageBox.critical(self, "Error en Benchmark", f"No se pudo completar el benchmark:\n{e}")
            self.statusBar().showMessage("Error al ejecutar benchmark.")

    def get_paths(self, algo_name: str) -> tuple[str, str, str]:
        """Calcula rutas del archivo original, comprimido y descomprimido."""
        if self.current_file_path:
            orig_path = self.current_file_path
            ext = Path(self.current_file_path).suffix
            comp_path = self.current_file_path + ("_comp.huff" if algo_name == "Huffman" else "_comp.lzw")
            dec_path = self.current_file_path + f"_dec_{algo_name}{ext}"
        else:
            Path("temp_run").mkdir(parents=True, exist_ok=True)
            orig_path = "temp_run/manual_input.txt"
            if not Path(orig_path).exists():
                save_text_file(orig_path, self.current_text, encoding="utf-8")
            comp_path = f"temp_run/manual_input_comp.{algo_name.lower()}"
            dec_path = f"temp_run/manual_input_dec_{algo_name}.txt"
        return orig_path, comp_path, dec_path

    def add_to_table(self, result: dict[str, Any]) -> None:
        """Agrega un resultado de métricas a la tabla comparativa."""
        row_idx = self.results_table.rowCount()
        self.results_table.insertRow(row_idx)

        # Rellenar columnas
        self.results_table.setItem(row_idx, 0, QTableWidgetItem(result["algorithm"]))
        self.results_table.setItem(row_idx, 1, QTableWidgetItem(f"{result['original_size_bytes']:,} bytes"))
        self.results_table.setItem(row_idx, 2, QTableWidgetItem(f"{result['compressed_size_bytes']:,} bytes"))
        self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{result['compression_ratio']:.4f}"))
        self.results_table.setItem(row_idx, 4, QTableWidgetItem(f"{result['reduction_percentage']:.2f}%"))
        self.results_table.setItem(row_idx, 5, QTableWidgetItem(f"{result['compression_time_seconds']:.6f} s"))
        self.results_table.setItem(row_idx, 6, QTableWidgetItem(f"{result['decompression_time_seconds']:.6f} s"))
        self.results_table.setItem(row_idx, 7, QTableWidgetItem("OK" if result["lossless"] else "ERROR"))

    def generate_report_string(self, result: dict[str, Any], orig_path: str, comp_path: str, dec_path: str) -> str:
        """Genera el bloque textual del reporte formateado."""
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

        report = (
            "========================================\n"
            f"REPORTE DE TEXTZIPLAB - {result['algorithm'].upper()}\n"
            "========================================\n\n"
            "ARCHIVO ORIGINAL\n"
            f"- Ruta: {orig_path}\n"
            f"- Nombre: {orig_name}\n"
            f"- Extensión: {orig_ext}\n"
            f"- Tamaño real: {orig_bytes:,} bytes\n"
            f"- Tamaño real: {orig_bits:,} bits\n\n"
            "TEXTO LEÍDO\n"
            f"- Codificación usada: {encoding}\n"
            f"- Caracteres totales: {total_caracteres:,}\n"
            f"- Caracteres sin espacios ni saltos de línea: {caracteres_sin_espacios:,}\n"
            f"- Palabras: {palabras:,}\n"
            f"- Líneas: {lineas:,}\n"
            f"- Tamaño lógico del texto leído: {logical_bytes:,} bytes\n"
            f"- Tamaño lógico del texto leído: {logical_bits:,} bits\n\n"
            "ARCHIVO COMPRIMIDO\n"
            f"- Ruta: {comp_path}\n"
            f"- Tamaño real: {comp_bytes:,} bytes\n"
            f"- Tamaño real: {comp_bits:,} bits\n\n"
            "ARCHIVO DESCOMPRIMIDO\n"
            f"- Ruta: {dec_path}\n"
            f"- Tamaño real: {dec_bytes:,} bytes\n"
            f"- Tamaño real: {dec_bits:,} bits\n\n"
            "VALIDACIÓN\n"
            f"- Original vs descomprimido byte a byte: {lossless_str}\n"
            f"- Diferencia de bytes: {diff_bytes:,}\n"
            f"- ¿Compresión sin pérdida?: {lossless_bool_str}\n\n"
            "RESULTADOS DE COMPRESIÓN\n"
            f"- Ratio de compresión: {ratio:.4f}\n"
            f"- Porcentaje comprimido respecto al original: {pct_comprimido:.2f}%\n"
            f"- Ahorro de espacio: {ahorro:.2f}%\n\n"
            "OBSERVACIÓN\n"
            "- El tamaño lógico del texto puede diferir del tamaño físico del archivo por codificación, saltos de línea o caracteres especiales.\n"
            "- La métrica principal de compresión compara el tamaño físico del archivo original contra el tamaño físico del archivo comprimido.\n"
            "========================================"
        )
        return report


def run_gui() -> None:
    """Arranca el bucle de eventos de la aplicación Qt."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
