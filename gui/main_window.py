"""Interfaz gráfica PySide6 para TextZipLab."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
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
    save_compressed_file,
    load_compressed_file,
    preview_compressed_data,
    validate_compressed_data,
)
from core.huffman import HuffmanCompressor
from core.lzw import LZWCompressor
from core.metrics import measure_algorithm, summarize_result
from experiments.benchmark import run_benchmark


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TextZipLab - Analizador y Compresor Multiformato")
        self.resize(1150, 800)

        # Variables de estado
        self.current_text: str = ""
        self.current_file_path: str | None = None
        self.current_encoding: str = "utf-8"
        self.last_results: list[dict[str, Any]] = []
        self.loaded_compressed_data: dict[str, Any] | None = None
        self.loaded_compressed_path: str | None = None
        self.decompressed_text_recovered: str | None = None

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
        # Widget y Layout principal vertical
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ------------------ CABECERA (HEADER BANNER) ------------------
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 5)
        header_layout.setSpacing(3)

        title_label = QLabel("TextZipLab")
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #a78bfa;")
        
        subtitle_label = QLabel("Laboratorio experimental y analizador comparativo de compresión de textos (Huffman vs LZW)")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setStyleSheet("color: #71717a; font-size: 12px;")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_widget)

        # ------------------ CONTENIDO SPLIT ------------------
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # ------------------ PANEL IZQUIERDO (CONTROLES) ------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Grupo: Carga de Archivo
        load_group = QGroupBox("Cargar Archivo de Texto")
        load_layout = QVBoxLayout(load_group)
        load_layout.setSpacing(12)

        self.load_button = QPushButton("Seleccionar archivo")
        self.load_button.setObjectName("load_button")
        self.load_button.clicked.connect(self.select_file)
        load_layout.addWidget(self.load_button)

        # Tarjeta para mostrar la información del archivo
        self.info_card = QFrame()
        self.info_card.setObjectName("file_info_card")
        card_layout = QVBoxLayout(self.info_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)

        self.file_info_label = QLabel("Ningún archivo cargado actualmente.")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setStyleSheet("color: #a1a1aa; line-height: 1.4;")
        card_layout.addWidget(self.file_info_label)
        
        load_layout.addWidget(self.info_card)
        left_layout.addWidget(load_group)

        # Grupo: Operaciones de Compresión
        ops_group = QGroupBox("Algoritmos y Operaciones")
        ops_layout = QVBoxLayout(ops_group)
        ops_layout.setSpacing(12)

        algo_label = QLabel("Seleccionar algoritmo principal:")
        algo_label.setStyleSheet("color: #a1a1aa; font-weight: 500;")
        ops_layout.addWidget(algo_label)
        
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

        # Grupo: Archivos Comprimidos
        persist_group = QGroupBox("Archivos Comprimidos")
        persist_layout = QVBoxLayout(persist_group)
        persist_layout.setSpacing(10)

        self.save_bin_button = QPushButton("Guardar comprimido real")
        self.save_bin_button.clicked.connect(self.save_compressed_bin)
        self.save_bin_button.setEnabled(False)
        persist_layout.addWidget(self.save_bin_button)

        self.load_compr_button = QPushButton("Cargar comprimido")
        self.load_compr_button.clicked.connect(self.load_compressed_file_gui)
        persist_layout.addWidget(self.load_compr_button)

        self.decompress_compr_button = QPushButton("Descomprimir")
        self.decompress_compr_button.clicked.connect(self.decompress_loaded_file)
        self.decompress_compr_button.setEnabled(False)
        persist_layout.addWidget(self.decompress_compr_button)

        self.view_recovered_full_button = QPushButton("Ver texto completo")
        self.view_recovered_full_button.clicked.connect(self.show_full_recovered_text_dialog)
        self.view_recovered_full_button.setEnabled(False)
        persist_layout.addWidget(self.view_recovered_full_button)

        self.save_recovered_button = QPushButton("Guardar recuperado")
        self.save_recovered_button.clicked.connect(self.save_recovered_text)
        self.save_recovered_button.setEnabled(False)
        persist_layout.addWidget(self.save_recovered_button)

        self.export_json_button = QPushButton("Exportar vista académica JSON")
        self.export_json_button.setObjectName("compare_button")
        self.export_json_button.clicked.connect(self.export_academic_json)
        self.export_json_button.setEnabled(False)
        persist_layout.addWidget(self.export_json_button)

        left_layout.addWidget(persist_group)
        left_layout.addStretch()

        left_panel.setFixedWidth(300)
        content_layout.addWidget(left_panel)

        # ------------------ PANEL DERECHO (RESULTADOS) ------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Área de Reporte de Texto
        report_title = QLabel("Reporte Detallado de Resultados")
        report_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e4e4e7;")
        right_layout.addWidget(report_title)
        
        self.report_area = QTextEdit()
        self.report_area.setReadOnly(True)
        self.report_area.setPlaceholderText("Los reportes analíticos y de validación en HTML aparecerán aquí al comprimir...")
        right_layout.addWidget(self.report_area, stretch=3)

        # Tabla Comparativa
        table_title = QLabel("Tabla de Métricas y Comparación")
        table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e4e4e7;")
        right_layout.addWidget(table_title)
        
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

        content_layout.addWidget(right_panel)
        main_layout.addWidget(content_widget)

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
                f"<div style='line-height: 1.5; color: #f4f4f5;'>"
                f"<b>Nombre:</b> <span style='color: #a78bfa;'>{name}</span><br>"
                f"<b>Tamaño:</b> {size:,} bytes<br>"
                f"<b>Codificación:</b> {enc}<br>"
                f"<b>Estadísticas:</b><br>"
                f"- {total_chars:,} caracteres<br>"
                f"- {words:,} palabras<br>"
                f"- {lines:,} líneas"
                f"</div>"
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

            # Generar reporte HTML
            report_html = self.generate_report_html(result, orig_path, comp_path, dec_path)
            self.report_area.setHtml(report_html)

            # Agregar a la tabla de resultados
            self.add_to_table(result)
            self.last_results.append(result)

            # Habilitar descompresión y persistencia
            self.decompress_button.setEnabled(True)
            self.save_bin_button.setEnabled(True)
            self.export_json_button.setEnabled(True)
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

            # Generar reportes HTML combinados
            h_report_html = self.generate_report_html(h_result, h_orig, h_comp, h_dec)
            l_report_html = self.generate_report_html(l_result, l_orig, l_comp, l_dec)

            best_reduction = max([h_result, l_result], key=lambda item: item["reduction_percentage"])
            fastest = min([h_result, l_result], key=lambda item: item["total_time_seconds"])

            comparison_html = (
                f"<div style=\"font-family: 'Segoe UI', sans-serif; color: #f4f4f5;\">"
                f"<h2 style=\"color: #a855f7; border-bottom: 2px solid #27272a; padding-bottom: 8px; margin-top: 0; text-align: center;\">"
                f"COMPARATIVA DIRECTA: HUFFMAN VS LZW</h2>"
                f"<div style=\"margin-top: 15px;\">{h_report_html}</div>"
                f"<div style=\"margin-top: 25px; border-top: 1px dashed #27272a; padding-top: 20px;\">{l_report_html}</div>"
                f"<div style=\"background-color: #1a1a2e; border: 1px solid #4c1d95; border-radius: 8px; padding: 16px; margin-top: 20px;\">"
                f"<h3 style=\"color: #a78bfa; margin-top: 0; margin-bottom: 8px; font-size: 13px; text-transform: uppercase;\">Conclusión Automática</h3>"
                f"<ul style=\"margin: 0; padding-left: 20px; color: #e4e4e7; font-size: 12px; line-height: 1.6;\">"
                f"<li style=\"margin-bottom: 6px;\">"
                f"<strong>Mejor reducción de espacio:</strong> <span style=\"color: #10b981; font-weight: bold;\">{best_reduction['algorithm']}</span> "
                f"({best_reduction['reduction_percentage']:.2f}% de ahorro)</li>"
                f"<li><strong>Mayor velocidad de procesamiento:</strong> <span style=\"color: #38bdf8; font-weight: bold;\">{fastest['algorithm']}</span> "
                f"({fastest['total_time_seconds']:.6f} segundos totales)</li>"
                f"</ul></div></div>"
            )
            self.report_area.setHtml(comparison_html)

            # Actualizar tabla comparativa
            self.results_table.setRowCount(0)
            self.add_to_table(h_result)
            self.add_to_table(l_result)

            self.last_results = [h_result, l_result]
            self.decompress_button.setEnabled(True)
            self.save_bin_button.setEnabled(True)
            self.export_json_button.setEnabled(True)
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
            
            # Formatear la tabla del benchmark en un pre bonito
            benchmark_html = (
                f"<div style=\"font-family: 'Segoe UI', sans-serif; color: #f4f4f5;\">"
                f"<h2 style=\"color: #a855f7; border-bottom: 2px solid #27272a; padding-bottom: 8px; margin-top: 0;\">"
                f"BENCHMARK EXPERIMENTAL COMPLETADO</h2>"
                f"<p style=\"color: #10b981; font-size: 12px; margin-bottom: 12px;\"><strong>Resultados guardados en:</strong> <code>experiments/results/results.csv</code></p>"
                f"<pre style=\"font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; font-size: 11px; background-color: #0c0a0f; padding: 14px; border: 1px solid #221d2b; border-radius: 8px; color: #e4e4e7; line-height: 1.4;\">{df.to_string(index=False)}</pre>"
                f"</div>"
            )
            self.report_area.setHtml(benchmark_html)
            
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
                
                # Crear item de validación coloreado
                validation_item = QTableWidgetItem("OK" if lossless else "ERROR")
                if lossless:
                    validation_item.setForeground(QColor("#10b981"))
                else:
                    validation_item.setForeground(QColor("#ef4444"))
                self.results_table.setItem(row_idx, 7, validation_item)
                
                # Estilo a las celdas añadidas
                for col in range(8):
                    item = self.results_table.item(row_idx, col)
                    if item:
                        # Negrita para la primera columna
                        if col == 0:
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        # Verde para columna ahorro
                        elif col == 4:
                            item.setForeground(QColor("#10b981"))
                            font = item.font()
                            font.setBold(True)
                            item.setFont(font)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
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
        """Agrega un resultado de métricas a la tabla comparativa con formato y color."""
        row_idx = self.results_table.rowCount()
        self.results_table.insertRow(row_idx)

        # Rellenar columnas
        self.results_table.setItem(row_idx, 0, QTableWidgetItem(result["algorithm"]))
        self.results_table.setItem(row_idx, 1, QTableWidgetItem(f"{result['original_size_bytes']:,} bytes"))
        self.results_table.setItem(row_idx, 2, QTableWidgetItem(f"{result['compressed_size_bytes']:,} bytes"))
        self.results_table.setItem(row_idx, 3, QTableWidgetItem(f"{result['compression_ratio']:.4f}"))
        
        # Columna de reducción con color verde destacado
        reduction_item = QTableWidgetItem(f"{result['reduction_percentage']:.2f}%")
        reduction_item.setForeground(QColor("#10b981"))
        self.results_table.setItem(row_idx, 4, reduction_item)
        
        self.results_table.setItem(row_idx, 5, QTableWidgetItem(f"{result['compression_time_seconds']:.6f} s"))
        self.results_table.setItem(row_idx, 6, QTableWidgetItem(f"{result['decompression_time_seconds']:.6f} s"))
        
        # Columna de validación con color según estado
        validation_item = QTableWidgetItem("OK" if result["lossless"] else "ERROR")
        if result["lossless"]:
            validation_item.setForeground(QColor("#10b981"))
        else:
            validation_item.setForeground(QColor("#ef4444"))
        self.results_table.setItem(row_idx, 7, validation_item)

        # Aplicar formato de alineación y tipografía
        for col in range(8):
            item = self.results_table.item(row_idx, col)
            if item:
                # Negrita para algoritmo y validación
                if col in [0, 4, 7]:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def generate_report_html(self, result: dict[str, Any], orig_path: str, comp_path: str, dec_path: str) -> str:
        """Genera el bloque HTML del reporte formateado."""
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
        
        ratio = result["compression_ratio"]
        pct_comprimido = result["porcentaje_comprimido"]
        ahorro = result["reduction_percentage"]
        
        orig_name = Path(orig_path).name
        orig_ext = Path(orig_path).suffix

        # Colores dinámicos
        lossless_color = "#10b981" if result["lossless"] else "#ef4444"
        lossless_bg = "#064e3b" if result["lossless"] else "#7f1d1d"
        lossless_border = "#047857" if result["lossless"] else "#b91c1c"
        
        lossless_badge = (
            f"<span style=\"color: {lossless_color}; background-color: {lossless_bg}; "
            f"border: 1px solid {lossless_border}; border-radius: 4px; padding: 2px 8px; "
            f"font-weight: bold; font-size: 11px;\">{lossless_str}</span>"
        )

        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; color: #f4f4f5; margin-bottom: 10px;">
            <h3 style="color: #a78bfa; margin-top: 0; margin-bottom: 12px; border-bottom: 1px solid #27272a; padding-bottom: 6px; text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px;">
                REPORTE DE TEXTZIPLAB - <span style="color: #6366f1;">{result['algorithm'].upper()}</span>
            </h3>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px;">
                <tr style="background-color: #1f1f2e;">
                    <td colspan="2" style="font-weight: bold; color: #a78bfa; padding: 6px 8px; border-radius: 4px;">ARCHIVO ORIGINAL</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa; width: 40%;">Nombre del archivo:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7; font-weight: bold;">{orig_name} <span style="color: #71717a; font-size: 11px; font-weight: normal;">({orig_ext})</span></td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Tamaño físico original:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7; font-family: monospace;">{orig_bytes:,} bytes ({orig_bits:,} bits)</td>
                </tr>
                
                <tr style="background-color: #1f1f2e;">
                    <td colspan="2" style="font-weight: bold; color: #a78bfa; padding: 6px 8px; border-radius: 4px;">TEXTO LEÍDO</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Codificación / Caracteres:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7;">{encoding} / {total_caracteres:,} caracteres</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Palabras / Líneas:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7;">{palabras:,} palabras / {lineas:,} líneas</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Tamaño lógico leído:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7; font-family: monospace;">{logical_bytes:,} bytes ({logical_bits:,} bits)</td>
                </tr>

                <tr style="background-color: #1f1f2e;">
                    <td colspan="2" style="font-weight: bold; color: #a78bfa; padding: 6px 8px; border-radius: 4px;">ARCHIVO COMPRIMIDO</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Ruta de salida:</td>
                    <td style="padding: 5px 8px; color: #a1a1aa; font-size: 11px; font-family: monospace;">{comp_path}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Tamaño físico comprimido:</td>
                    <td style="padding: 5px 8px; color: #10b981; font-weight: bold; font-family: monospace;">{comp_bytes:,} bytes ({comp_bits:,} bits)</td>
                </tr>

                <tr style="background-color: #1f1f2e;">
                    <td colspan="2" style="font-weight: bold; color: #a78bfa; padding: 6px 8px; border-radius: 4px;">VALIDACIÓN E INTEGRIDAD</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Original vs Descomprimido:</td>
                    <td style="padding: 5px 8px;">{lossless_badge}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Diferencia de bytes:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7; font-family: monospace;">{diff_bytes:,} bytes</td>
                </tr>

                <tr style="background-color: #1f1f2e;">
                    <td colspan="2" style="font-weight: bold; color: #a78bfa; padding: 6px 8px; border-radius: 4px;">RESULTADOS DE COMPRESIÓN</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Ratio de compresión:</td>
                    <td style="padding: 5px 8px; color: #e4e4e7; font-family: monospace;">{ratio:.4f}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 8px; color: #a1a1aa;">Porcentaje / Ahorro:</td>
                    <td style="padding: 5px 8px; color: #10b981; font-weight: bold;">{pct_comprimido:.2f}% (Ahorro del {ahorro:.2f}%)</td>
                </tr>
            </table>
        </div>
        """
        return html

    def save_compressed_bin(self) -> None:
        """Guarda la última compresión de la sesión en un archivo binario real (.huff / .lzw)."""
        if not self.last_results:
            QMessageBox.warning(self, "Sin datos", "No hay ninguna compresión en memoria para guardar.")
            return

        last_res = self.last_results[-1]
        compressed_data = last_res.get("compressed_data")
        if not compressed_data:
            QMessageBox.warning(self, "Sin datos", "No se encontraron los datos comprimidos.")
            return

        algo = compressed_data.get("algorithm", "Compressed")
        ext = ".huff" if algo == "Huffman" else ".lzw"
        filter_str = f"Archivo Comprimido {algo} (*{ext})"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo comprimido REAL", f"resultado{ext}", filter_str
        )
        if not file_path:
            return

        try:
            if not file_path.lower().endswith(ext):
                file_path += ext

            # Inyectar metadatos de extensión, codificación y nombre original en la cabecera
            orig_path = self.current_file_path if self.current_file_path else "temp_run/manual_input.txt"
            compressed_data["original_extension"] = Path(orig_path).suffix
            compressed_data["original_encoding"] = self.current_encoding if hasattr(self, 'current_encoding') else "utf-8"
            compressed_data["original_name"] = Path(orig_path).name
            compressed_data["original_size_bytes"] = get_file_size_bytes(orig_path) if self.current_file_path else len(self.current_text.encode(compressed_data["original_encoding"]))

            save_compressed_file(file_path, compressed_data)
            size = get_file_size_bytes(file_path)
            
            QMessageBox.information(
                self, "Guardado Exitoso",
                f"El archivo binario comprimido se guardó correctamente en:\n{file_path}\n\n"
                f"Tamaño físico real: {size:,} bytes."
            )
            self.statusBar().showMessage(f"Comprimido real guardado: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def export_academic_json(self) -> None:
        """Exporta la compresión en formato JSON legible para análisis académico."""
        if not self.last_results:
            QMessageBox.warning(self, "Sin datos", "No hay ninguna compresión en memoria para exportar.")
            return

        last_res = self.last_results[-1]
        compressed_data = last_res.get("compressed_data")
        if not compressed_data:
            QMessageBox.warning(self, "Sin datos", "No se encontraron los datos comprimidos.")
            return

        algo = compressed_data.get("algorithm", "Compressed")
        ext = ".huff.json" if algo == "Huffman" else ".lzw.json"
        filter_str = f"Vista Académica JSON (*{ext})"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar vista académica JSON", f"resultado{ext}", filter_str
        )
        if not file_path:
            return

        try:
            if not file_path.lower().endswith(ext):
                file_path += ext

            orig_path = self.current_file_path if self.current_file_path else "temp_run/manual_input.txt"
            compressed_data["original_extension"] = Path(orig_path).suffix
            compressed_data["original_encoding"] = self.current_encoding if hasattr(self, 'current_encoding') else "utf-8"
            compressed_data["original_name"] = Path(orig_path).name
            compressed_data["original_size_bytes"] = get_file_size_bytes(orig_path) if self.current_file_path else len(self.current_text.encode(compressed_data["original_encoding"]))

            save_compressed_file(file_path, compressed_data)
            size = get_file_size_bytes(file_path)
            
            QMessageBox.information(
                self, "Exportado Exitoso",
                f"La vista académica JSON se exportó correctamente en:\n{file_path}\n\n"
                f"Tamaño físico del JSON: {size:,} bytes.\n\n"
                f"Nota: Este archivo es legible por humanos y contiene metadatos en texto claro, "
                f"por lo que pesa más que el archivo comprimido real."
            )
            self.statusBar().showMessage(f"Vista académica JSON exportada: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    def load_compressed_file_gui(self) -> None:
        """Carga y valida un archivo comprimido binario o JSON."""
        allowed_filters = "Archivos Comprimidos (*.huff *.lzw *.huff.json *.lzw.json);;Todos los archivos (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Cargar archivo comprimido", "", allowed_filters)
        
        if not file_path:
            return

        try:
            loaded_data = load_compressed_file(file_path)
            self.loaded_compressed_data = loaded_data
            self.loaded_compressed_path = file_path
            
            # Limpiar estado recuperado previo
            self.decompressed_text_recovered = None
            self.save_recovered_button.setEnabled(False)
            self.view_recovered_full_button.setEnabled(False)
            
            # Habilitar botones correspondientes
            self.decompress_compr_button.setEnabled(True)
            
            name = Path(file_path).name
            algo = loaded_data.get("algorithm")
            
            # Control de compatibilidad
            orig_name = loaded_data.get("original_name")
            orig_ext = loaded_data.get("original_extension")
            orig_enc = loaded_data.get("original_encoding")
            
            name_str = orig_name if orig_name is not None else "No disponible"
            ext_str = orig_ext if orig_ext is not None else "No disponible"
            enc_str = orig_enc if orig_enc is not None else "No disponible"
            
            self.statusBar().showMessage(f"Archivo cargado: {name} ({algo})")
            
            self.report_area.setHtml(
                f"<div style=\"font-family: 'Segoe UI', sans-serif; color: #f4f4f5;\">"
                f"<h3 style=\"color: #10b981; margin-top: 0;\">¡Archivo Comprimido Cargado con Éxito!</h3>"
                f"<b>Ruta de archivo comprimido:</b> <code>{file_path}</code><br>"
                f"<b>Algoritmo:</b> <span style=\"color: #a78bfa; font-weight: bold;\">{algo}</span><br>"
                f"<b>Nombre original en cabecera:</b> <code>{name_str}</code><br>"
                f"<b>Extensión original en cabecera:</b> <code>{ext_str}</code><br>"
                f"<b>Codificación en cabecera:</b> <code>{enc_str}</code><br><br>"
                f"<i>Presione 'Descomprimir' para recuperar el texto original y comparar sus métricas físicas y lógicas.</i>"
                f"</div>"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar el archivo:\n{e}")
            self.statusBar().showMessage("Error al cargar archivo.")

    def decompress_loaded_file(self) -> None:
        """Descomprime los datos cargados desde el archivo comprimido (binario o JSON)."""
        if not self.loaded_compressed_data:
            QMessageBox.warning(self, "Sin datos", "No hay ningún archivo comprimido cargado.")
            return

        algo = self.loaded_compressed_data.get("algorithm")
        self.statusBar().showMessage(f"Descomprimiendo con {algo}...")
        QApplication.processEvents()

        try:
            if algo == "Huffman":
                compressor = HuffmanCompressor()
            elif algo == "LZW":
                compressor = LZWCompressor()
            else:
                raise ValueError(f"Algoritmo desconocido: {algo}")

            decompressed_text = compressor.decompress(self.loaded_compressed_data)
            self.decompressed_text_recovered = decompressed_text
            self.save_recovered_button.setEnabled(True)
            self.view_recovered_full_button.setEnabled(True)
            
            # Vista previa del texto recuperado (hasta 5000 caracteres)
            lim = 5000
            preview_snippet = decompressed_text[:lim]
            is_partial = len(decompressed_text) > lim
            text_badge = f"<span style='color: #f59e0b; font-weight: bold;'>[VISTA PREVIA PARCIAL - Mostrando primeros 5,000 caracteres]</span>" if is_partial else f"<span style='color: #10b981; font-weight: bold;'>[CONTENIDO COMPLETO]</span>"
            
            # Reemplazar caracteres HTML especiales en la vista previa
            preview_snippet_html = (
                preview_snippet.replace("&", "&amp;")
                               .replace("<", "&lt;")
                               .replace(">", "&gt;")
                               .replace("\n", "<br>")
            )
            
            # Calcular tamaño real del texto recuperado
            orig_enc = self.loaded_compressed_data.get("original_encoding")
            if orig_enc is None:
                orig_enc = "utf-8"
            
            rec_bytes = len(decompressed_text.encode(orig_enc))
            rec_bits = rec_bytes * 8
            
            # Cabeceras y metadatos cargados
            orig_bytes = self.loaded_compressed_data.get("original_size_bytes")
            comp_bits_theoretical = self.loaded_compressed_data.get("compressed_size_bits")
            orig_name = self.loaded_compressed_data.get("original_name")
            orig_ext = self.loaded_compressed_data.get("original_extension")
            
            file_bytes_disk = get_file_size_bytes(self.loaded_compressed_path) if self.loaded_compressed_path else 0
            file_bits_disk = file_bytes_disk * 8
            
            is_json = self.loaded_compressed_path.lower().endswith(".json") if self.loaded_compressed_path else False
            
            # Formatear filas de metadatos originales
            if orig_bytes is not None:
                orig_bits = orig_bytes * 8
                orig_bytes_str = f"{orig_bytes:,} bytes ({orig_bits:,} bits)"
            else:
                orig_bytes_str = "No disponible"
                
            if comp_bits_theoretical is not None:
                comp_bytes_theoretical = (comp_bits_theoretical + 7) // 8
                comp_bits_str = f"{comp_bytes_theoretical:,} bytes ({comp_bits_theoretical:,} bits)"
                if orig_bytes is not None and orig_bytes > 0:
                    ratio_theoretical = comp_bits_theoretical / (orig_bytes * 8)
                    pct_theoretical = (1.0 - ratio_theoretical) * 100
                    theoretical_saving_str = f"{pct_theoretical:.2f}% (Ratio: {ratio_theoretical:.4f})"
                else:
                    theoretical_saving_str = "No disponible"
            else:
                comp_bits_str = "No disponible"
                theoretical_saving_str = "No disponible"
                
            if orig_bytes is not None and orig_bytes > 0:
                ratio_disk = file_bytes_disk / orig_bytes
                pct_disk = (1.0 - ratio_disk) * 100
                disk_saving_str = f"{pct_disk:.2f}% (Ratio: {ratio_disk:.4f})"
            else:
                disk_saving_str = "No disponible"
                
            name_sugerido = "archivo_recuperado.txt"
            if orig_name:
                orig_name_stem = Path(orig_name).stem
                ext = orig_ext if orig_ext else ".txt"
                name_sugerido = f"{orig_name_stem}_recuperado{ext}"
            elif orig_ext:
                name_sugerido = f"archivo_recuperado{orig_ext}"
                
            academic_note = ""
            if is_json:
                academic_note = (
                    f"<div style='font-size: 11px; color: #71717a; padding: 8px; background-color: #0c0a0f; border-left: 3px solid #f59e0b; border-radius: 4px;'>"
                    f"<b>Aclaración Académica:</b> El archivo JSON físico guardado en disco pesa más que el tamaño teórico del algoritmo. Esto ocurre porque el JSON es texto plano y contiene metadatos explicativos legibles por humanos (como alfabeto o diccionario) necesarios para la descompresión posterior."
                    f"</div>"
                )
            else:
                academic_note = (
                    f"<div style='font-size: 11px; color: #71717a; padding: 8px; background-color: #0c0a0f; border-left: 3px solid #10b981; border-radius: 4px;'>"
                    f"<b>Nota de Archivo Binario:</b> El archivo binario real guardado en disco tiene un peso físico muy cercano al tamaño teórico del algoritmo. Esto demuestra el beneficio de usar cabeceras estructuradas compactas de metadatos ('TZHUF1' o 'TZLZW1') y empaquetamiento a nivel de bits."
                    f"</div>"
                )

            html_report = (
                f"<div style=\"font-family: 'Segoe UI', sans-serif; color: #f4f4f5;\">"
                f"<h3 style=\"color: #10b981; border-bottom: 2px solid #27272a; padding-bottom: 5px; margin-top: 0;\">DESCOMPRESIÓN EXITOSA</h3>"
                f"<p><b>Algoritmo usado:</b> <span style='color: #a78bfa; font-weight: bold;'>{algo}</span></p>"
                f"<p><b>Archivo comprimido:</b> <code>{Path(self.loaded_compressed_path).name if self.loaded_compressed_path else 'Cargado'}</code></p>"
                
                f"<table style=\"width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 15px;\">"
                f"<tr style='background-color: #1a1a2e;'><td colspan='2' style='font-weight: bold; color: #a78bfa; padding: 6px 8px;'>MÉTRICAS REALES DE DISCO Y DE SALIDA</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Tamaño Físico del Comprimido:</td><td style='padding: 4px 8px; color: #38bdf8;'>{file_bytes_disk:,} bytes ({file_bits_disk:,} bits)</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Tamaño del Texto Recuperado:</td><td style='padding: 4px 8px; color: #10b981; font-weight: bold;'>{rec_bytes:,} bytes ({rec_bits:,} bits)</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Cantidad de Caracteres:</td><td style='padding: 4px 8px;'>{len(decompressed_text):,} caracteres</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Nombre sugerido de salida:</td><td style='padding: 4px 8px; font-family: monospace; font-size: 11px;'>{name_sugerido}</td></tr>"
                
                f"<tr style='background-color: #1a1a2e;'><td colspan='2' style='font-weight: bold; color: #a78bfa; padding: 6px 8px; margin-top: 10px;'>MÉTRICAS HISTÓRICAS DE COMPRESIÓN</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Tamaño Físico Original:</td><td style='padding: 4px 8px;'>{orig_bytes_str}</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Tamaño Comprimido Teórico (Bitstream):</td><td style='padding: 4px 8px;'>{comp_bits_str}</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Ahorro Teórico de Espacio:</td><td style='padding: 4px 8px;'>{theoretical_saving_str}</td></tr>"
                f"<tr><td style='padding: 4px 8px; color: #a1a1aa;'>Ahorro Real en Disco:</td><td style='padding: 4px 8px;'>{disk_saving_str}</td></tr>"
                f"</table>"
                
                f"<div style='margin-bottom: 8px;'><b>Vista Previa del Contenido Recuperado:</b> {text_badge}</div>"
                f"<div style='background-color: #111827; border: 1px solid #1f2937; padding: 10px; border-radius: 6px; margin-bottom: 12px; font-family: monospace; font-size: 11px; color: #e4e4e7; max-height: 250px; overflow-y: auto; text-align: left;'>"
                f"{preview_snippet_html}"
                f"</div>"
                f"{academic_note}"
                f"</div>"
            )
            self.report_area.setHtml(html_report)
            self.statusBar().showMessage("Texto descomprimido correctamente. Listo para visualizar y guardar.")
        except Exception as e:
            QMessageBox.critical(self, "Error al Descomprimir", f"Ocurrió un error en la descompresión:\n{e}")
            self.statusBar().showMessage("Error al descomprimir archivo.")

    def save_recovered_text(self) -> None:
        """Guarda el texto recuperado de la descompresión en un archivo."""
        if self.decompressed_text_recovered is None:
            QMessageBox.warning(self, "Sin datos", "No hay ningún texto recuperado listo para guardar.")
            return

        orig_name = self.loaded_compressed_data.get("original_name")
        orig_ext = self.loaded_compressed_data.get("original_extension")
        orig_enc = self.loaded_compressed_data.get("original_encoding")
        
        if not orig_ext:
            orig_ext = ".txt"
        if not orig_enc:
            orig_enc = "utf-8"
            
        name_sugerido = "archivo_recuperado.txt"
        if orig_name:
            orig_name_stem = Path(orig_name).stem
            name_sugerido = f"{orig_name_stem}_recuperado{orig_ext}"
        elif orig_ext:
            name_sugerido = f"archivo_recuperado{orig_ext}"
            
        allowed_filters = f"Archivos con extensión original (*{orig_ext});;Todos los archivos (*.*)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar texto recuperado", name_sugerido, allowed_filters)
        
        if not file_path:
            return

        try:
            save_text_file(file_path, self.decompressed_text_recovered, encoding=orig_enc)
            QMessageBox.information(
                self, "Guardado Exitoso",
                f"El texto recuperado se guardó correctamente en:\n{file_path}\n"
                f"Codificación: {orig_enc}"
            )
            self.statusBar().showMessage(f"Texto recuperado guardado: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")

    def show_full_recovered_text_dialog(self) -> None:
        """Abre un diálogo modal para ver la totalidad del texto recuperado."""
        if self.decompressed_text_recovered is None:
            QMessageBox.warning(self, "Sin datos", "No hay ningún texto recuperado disponible.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Visor de Texto Recuperado Completo")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(self.decompressed_text_recovered)
        
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #09090b;
                color: #e4e4e7;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(text_edit)
        
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(dialog.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #1f2937;
                color: #e4e4e7;
                border: 1px solid #374151;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #374151;
            }
        """)
        layout.addWidget(close_button)
        
        dialog.exec()


def run_gui() -> None:
    """Arranca el bucle de eventos de la aplicación Qt."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
