# TextZipLab

**Título formal:** Compresor Experimental de Archivos de Texto usando Huffman y LZW: análisis comparativo de complejidad temporal, espacial y rendimiento experimental.

## Descripción

TextZipLab es una aplicación académica desarrollada en Python para la compresión y descompresión de archivos textuales utilizando algoritmos sin pérdida (Lossless), principalmente **Huffman Coding** y **LZW (Lempel-Ziv-Welch)**. 

El proyecto cuenta con una interfaz interactiva de consola (CLI) y una interfaz gráfica premium basada en **PySide6** para comparar métricas experimentales en el análisis y diseño de algoritmos de compresión.

---

## Objetivo Principal

1. **Lectura Correcta y Robusta:** Cargar y analizar archivos textuales en codificaciones UTF-8, UTF-8-SIG y Latin-1 sin alterar el contenido original (preservando saltos de línea CRLF/LF).
2. **Medición Precisa:** Separar conceptualmente los tipos de tamaño (físico, lógico, en disco), caracteres y bits para reportes rigurosos.
3. **Compresión Física Real:** Utilizar un formato binario compacto personalizado para almacenar archivos `.huff` y `.lzw` con un overhead mínimo en disco, en lugar de serializadores pesados como `pickle`.
4. **Validación Byte a Byte:** Asegurar la integridad absoluta comparando el archivo original contra el descomprimido a nivel de bytes directos.
5. **Reporte Académico Completo:** Generar estadísticas, ratios, tiempos y comparativas ideales para informes científicos.

---

## Conceptos Clave y Fórmulas de Medición

Para evitar confusiones en el reporte de resultados, el programa distingue rigurosamente las siguientes métricas:

### A. Bytes vs Bits vs Caracteres
* **Caracteres totales:** Cantidad de símbolos en el texto plano (`len(texto)`), incluyendo letras, números, espacios y saltos de línea.
* **Caracteres sin espacios:** Longitud tras omitir `" "`, `\n`, `\r`, y `\t`.
* **Diferencia entre caracteres y bytes:** Un carácter no equivale siempre a un byte. Bajo UTF-8, caracteres estándar ASCII ocupan 1 byte, pero caracteres con tildes (como `á`), eñes (`ñ`), emojis (como `🚀`) y caracteres coreanos ocupan de 2 a 4 bytes.
* **Bits:** Conversión directa física y lógica: `bits = bytes * 8`.

### B. Tamaños del Archivo
* **Tamaño Físico Real (Original / Comprimido / Descomprimido):** Calculado con `os.path.getsize(ruta_archivo)`. Representa el peso real del archivo físico en bytes y es el valor equivalente al campo **"Tamaño"** de Windows.
* **Tamaño en Disco:** Depende del sistema de archivos y el tamaño de clúster (por ejemplo, bloques de 4,096 bytes). Un archivo de 3,399 bytes lógicos puede ocupar 4,096 bytes en disco. TextZipLab aclara esta diferencia en sus reportes pero no la usa para medir la tasa de compresión.
* **Tamaño Lógico del Texto Leído:** Calculado en memoria codificando el texto nuevamente: `len(texto.encode(encoding_usado))`. Puede variar respecto al tamaño físico si el archivo original poseía marcas de orden de bytes (BOM) u otras codificaciones no compatibles.

### C. Fórmulas de Compresión
Las métricas principales de compresión se basan únicamente en los tamaños físicos reales de los archivos en disco:
* **Ratio de Compresión:**
  $$\text{Ratio} = \frac{\text{Tamaño Físico Comprimido (bytes)}}{\text{Tamaño Físico Original (bytes)}}$$
* **Porcentaje Comprimido:**
  $$\text{Porcentaje Comprimido} = \text{Ratio} \times 100$$
* **Ahorro de Espacio:**
  $$\text{Ahorro} = (1 - \text{Ratio}) \times 100$$

*Ejemplo:* Si el archivo original pesa 3,399 bytes y el comprimido pesa 2,000 bytes, el ratio es $0.5884$, el porcentaje comprimido es $58.84\%$ y el ahorro es $41.16\%$.

### D. Compresión Sin Pérdida (Validation)
Se realiza leyendo en modo binario puro (`"rb"`) tanto el archivo original como el descomprimido final:
```python
def comparar_archivos_byte_a_byte(ruta1, ruta2):
    with open(ruta1, "rb") as f1, open(ruta2, "rb") as f2:
        return f1.read() == f2.read()
```
Si coinciden bit a bit en disco, la validación se reporta como `OK` (`SÍ`).

---

## Formatos de Texto Soportados

TextZipLab restringe la lectura a formatos textuales para evitar fallas al procesar archivos binarios. Las extensiones permitidas son:
```text
.txt, .csv, .json, .xml, .html, .htm, .css, .js, .py, .java, .cpp, .c, .md, .log, .ini, .cfg, .yaml, .yml, .sql
```
*Nota:* El programa rechazará archivos binarios como `.exe`, `.pdf`, `.png`, `.jpg`, `.docx` mostrando una advertencia clara.

---

## Arquitectura del Proyecto

```text
TextZipLab/
│
├── main.py                    # Orquestador del menú principal (Consola/GUI)
├── requirements.txt           # Dependencias de Python (PySide6, pandas, etc.)
├── README.md                  # Este documento
│
├── core/
│   ├── bit_utils.py           # Utilidades para empaquetado de cadenas de bits
│   ├── file_manager.py        # Lectura robusta y serialización binaria compacta
│   ├── huffman.py             # Algoritmo de compresión Huffman
│   ├── lzw.py                 # Algoritmo de compresión LZW
│   ├── metrics.py             # Medición temporal, espacial y ratios en disco
│   └── validator.py           # Validación byte a byte física
│
├── gui/
│   ├── main_window.py         # Interfaz gráfica premium (PySide6)
│   └── styles.qss             # Estilos de tema oscuro moderno
│
├── experiments/
│   ├── benchmark.py           # Script para correr pruebas automatizadas
│   ├── test_generator.py      # Generador de escenarios (patrones, aleatorios)
│   └── results/
│       └── results.csv        # Archivo con resultados acumulados del benchmark
│
└── tests/                     # Suite de pruebas automatizadas
    ├── test_file_manager.py
    ├── test_huffman.py
    ├── test_lzw.py
    ├── test_integrity.py
    └── test_special_cases.py  # Casos con emojis, coreano, tildes, vacíos, etc.
```

---

## Cómo Ejecutar el Proyecto

### 1. Instalar Dependencias
Asegúrate de contar con Python 3.10 o superior y ejecuta:
```bash
pip install -r requirements.txt
```

### 2. Iniciar TextZipLab (Consola o Interfaz Gráfica)
Ejecuta el archivo principal:
```bash
python main.py
```
Se mostrará un menú interactivo inicial para elegir el modo de ejecución:
```text
=== TextZipLab ===
1. Ejecutar en Consola (CLI)
2. Ejecutar con Interfaz Gráfica (GUI - PySide6)
```

También puedes forzar el inicio de la **Interfaz Gráfica de Usuario (GUI)** directamente usando el argumento `--gui`:
```bash
python main.py --gui
```

### 3. Ejecutar Benchmark Académico
Para analizar los algoritmos bajo diferentes tamaños y tipos de datos (repetitivos, patrones, código, CSV) y generar el dataset experimental:
```bash
python experiments/benchmark.py
```

### 4. Ejecutar Pruebas Unitarias
Para correr la batería completa de 22 pruebas automatizadas (cobertura de casos extremos y unicode):
```bash
python -m pytest
```

---

## Ejemplo de Reporte Generado

```text
========================================
REPORTE DE TEXTZIPLAB - HUFFMAN
========================================

ARCHIVO ORIGINAL
- Ruta: C:/Users/Mila/Downloads/TextZipLab/samples/sample.txt
- Nombre: sample.txt
- Extensión: .txt
- Tamaño real: 3,399 bytes
- Tamaño real: 27,192 bits

TEXTO LEÍDO
- Codificación usada: UTF-8
- Caracteres totales: 2,531
- Caracteres sin espacios ni saltos de línea: 2,001
- Palabras: 412
- Líneas: 177
- Tamaño lógico del texto leído: 3,222 bytes
- Tamaño lógico del texto leído: 25,776 bits

ARCHIVO COMPRIMIDO
- Ruta: C:/Users/Mila/Downloads/TextZipLab/samples/sample.txt_comp.huff
- Tamaño real: 2,000 bytes
- Tamaño real: 16,000 bits

ARCHIVO DESCOMPRIMIDO
- Ruta: C:/Users/Mila/Downloads/TextZipLab/samples/sample.txt_dec_Huffman.txt
- Tamaño real: 3,399 bytes
- Tamaño real: 27,192 bits

VALIDACIÓN
- Original vs descomprimido byte a byte: OK
- Diferencia de bytes: 0
- ¿Compresión sin pérdida?: SÍ

RESULTADOS DE COMPRESIÓN
- Ratio de compresión: 0.5884
- Porcentaje comprimido respecto al original: 58.84%
- Ahorro de espacio: 41.16%

OBSERVACIÓN
- El tamaño lógico del texto puede diferir del tamaño físico del archivo por codificación, saltos de línea o caracteres especiales.
- La métrica principal de compresión compara el tamaño físico del archivo original contra el tamaño físico del archivo comprimido.
========================================
```

---

## Limitaciones
* **Archivos Binarios:** TextZipLab está diseñado específicamente para textos planos. Formatos ya comprimidos (como `.zip`, `.rar`, `.png`, `.jpg`) u ofimáticos binarios (`.docx`, `.xlsx`, `.pdf`) serán rechazados para evitar corrupción.
* **Archivos Extremadamente Grandes:** Para archivos con escalas del orden de $10^{10}$ caracteres, la ejecución física en memoria puede saturar la RAM si no se realiza por streaming de bloques; por ende, estos casos extremos se calculan teórica u experimentalmente por extrapolación en el benchmark.
