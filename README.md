
for running:
python cli.py dataset/file.pdf (if a folder is specified all the files inside are processed) --rapidocr (other options --openai, if not specified easyocr will be used) 





# 📄 Docling PDF Processor

Welcome to the **Docling PDF Processor**! This tool leverages the power of [Docling](https://github.com/DS4SD/docling) to seamlessly convert PDF documents into structured Markdown, handling complex elements like images and multi-page tables with ease. 🚀

## ✨ Features & Problems Solved

This project addresses several common challenges when extracting content from PDFs:

### 1. 📝 PDF to Markdown Conversion
Directly converts PDF files into clean, readable **Markdown** format. No more copy-pasting or dealing with messy text extraction! The structure (headers, paragraphs, lists) is preserved.

### 2. 🖼️ Image Extraction
Automatically detects and extracts **images** embedded within the PDF. Each image is saved as a separate file (e.g., `.png`, `.jpg`) in a dedicated `images/` directory, ensuring no visual asset is lost.

### 3. 🔗 Context-Aware Image Insertion
Instead of just dumping images into a folder, this tool inserts **links** to the extracted images directly into the generated Markdown file. 
*   **Problem Solved:** Images appear in their correct context within the text, maintaining the original flow of the document. `![Image](images/picture_0.png)` tags are placed exactly where the image belongs.

### 4. 📊 Multi-Page Table Merging
PDFs often split large tables across multiple pages, breaking headers and structure.
*   **Problem Solved:** This tool intelligently detects and **merges** split tables into single, unified CSV files and Markdown tables.
    *   It handles repeated headers (skipping them in the merge).
    *   It detects "lost" header rows that might be interpreted as data and restores them.
    *   The result is a single, continuous table in your output, ready for analysis.

## 🛠️ Setup

1.  **Clone the repository** (or copy the files).
2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 Usage

1.  Place your target PDF file in the project root and name it `file.pdf` (or update the script to point to your file).
2.  Run the script:
    ```bash
    python cli.py
    ```
3.  **Check the output:**
    *   `output.md`: Your fully formatted Markdown file.
    *   `output.json`: The raw structured data from Docling.
    *   `images/`: Folder containing all extracted images.
    *   `tables/`: Folder containing merged CSVs of the detected tables.

## 📦 Requirements

*   Python 3.10+
*   `docling`
*   `pandas`
*   `tabulate`
*   `Pillow`

---
*Happy Parsing!* 🕵️‍♀️📄
