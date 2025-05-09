import os
import io
import PyPDF2
from docx import Document
from pathlib import Path
from fpdf import FPDF
import requests
import argparse
from tqdm import tqdm
import logging
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from unstructured.partition.auto import partition
from unstructured.documents.elements import Text, Table

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text_from_file(file_path, use_ocr=False):
    """
    Extracts text from various file types (PDF, DOCX, TXT, etc.) using unstructured.

    Args:
        file_path: Path to the file.
        use_ocr: Boolean, whether to use OCR for PDFs if text extraction fails.

    Returns:
        The extracted text as a string, or None if extraction fails.
    """
    file_path = Path(file_path)
    logging.info(f"Extracting text from: {file_path}")
    text = ""

    try:
        # Step 1: Attempt text extraction using unstructured
        try:
            with open(file_path, "rb") as f:
                elements = partition(file=f, ocr_languages="eng")
                for element in elements:
                    if isinstance(element, (Text, Table)):
                        text += element.text + "\n"
        except Exception as e:
            logging.warning(f"Initial text extraction failed for {file_path}: {e}")

        # Step 2: If no text is found and OCR is enabled for PDFs, attempt OCR
        if not text.strip() and use_ocr and file_path.suffix.lower() == ".pdf":
            logging.info(f"No text found in PDF, attempting OCR: {file_path}")
            try:
                # Convert PDF pages to images
                images = convert_from_path(file_path)
                ocr_text = ""
                for image in images:
                    ocr_text += pytesseract.image_to_string(image)
                text = ocr_text.strip()
            except Exception as e:
                logging.error(f"OCR failed for {file_path} with error: {e}")

        # Step 3: If no text is found after OCR, log a warning
        if not text.strip():
            logging.warning(f"Failed to extract text from {file_path} using both methods.")
            return None

        # Step 4: Replace ligatures and other special characters
        ligature_replacements = {
            chr(64257): "fi",  # Ligature fi
            chr(64258): "fl",  # Ligature fl
            chr(64256): "ff",  # Ligature ff
            "\ufb01": "fi",    # Ligature fi (alternative)
        }
        for char, replacement in ligature_replacements.items():
            text = text.replace(char, replacement)

        return text

    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
        return None

def download_DejaVu_if_not_exists(filename, url):
    if not os.path.exists(filename):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for bad status codes
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Downloaded and saved to root directory: {filename}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading file: {e}")
        except Exception as e:
            logging.error(f"Error: {e}")
    else:
        logging.info(f"File already exists: {filename}")

def chunk_text_into_pdfs_fpdf(text, output_dir, pages_per_pdf=500, base_filename="chunk"):
    """
    Chunks text into multiple PDF files using FPDF, limiting pages per PDF.

    :param text: The input text to be split into PDFs.
    :param output_dir: The directory where PDFs will be saved.
    :param pages_per_pdf: Maximum number of pages per PDF.
    :param base_filename: Base name for the output PDF files.
    """
    try:
        download_DejaVu_if_not_exists("DejaVuSans.ttf", "https://raw.githubusercontent.com/x-cod3r/Automated-Anki-Flash-card-generator/refs/heads/main/DejaVuSans.ttf")
    except Exception as e:
        logging.error(f"Error downloading font file: {e}")
        return

    try:
        os.makedirs(output_dir, exist_ok=True)
        text_lines = text.splitlines()
        chunk_num = 1
        pdf = FPDF()  # No encoding parameter needed
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Use a font that supports UTF-8 (e.g., DejaVuSans)
        pdf.add_font("DejaVuSans", style="", fname="DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVuSans", size=9)  # Set the font to DejaVuSans

        for line in text_lines:
            # Skip empty or blank lines
            if not line.strip():
                continue

            # Start a new PDF if the page limit is reached
            if pdf.page_no() >= pages_per_pdf:
                pdf.output(os.path.join(output_dir, f"{base_filename}_{chunk_num:02d}.pdf"))
                pdf = FPDF()  # Start a new PDF
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_font("DejaVuSans", style="", fname="DejaVuSans.ttf", uni=True)
                pdf.set_font("DejaVuSans", size=9)  # Set the font to DejaVuSans
                chunk_num += 1

            # Add a new page if this is the first line of the PDF
            if pdf.page_no() == 0:
                pdf.add_page()

            # Add the line to the PDF
            pdf.multi_cell(0, 5, txt=line)

        # Save the last PDF if it contains any pages
        if pdf.page_no() > 0:
            pdf.output(os.path.join(output_dir, f"{base_filename}_{chunk_num:02d}.pdf"))

        logging.info(f'Created {chunk_num} PDFs using FPDF.')

        if os.path.exists("DejaVuSans.pkl") or os.path.exists("DejaVuSans.cw127.pkl"): # Clean up font cache files
                os.remove("DejaVuSans.pkl")
                os.remove("DejaVuSans.cw127.pkl")
                logging.info("Removed font cache files.")
        else:
                logging.info("Font cache files not found.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

def process_files(input_path, output_dir, pages_per_pdf=500, use_ocr=False, pdf_engine="reportlab"):
    """
    Processes a single file or all files in a directory.

    Args:
        input_path: Path to a single file or a directory containing files.
        output_dir: Directory to save output PDF chunks.
        pages_per_pdf: Maximum pages per output PDF.
        use_ocr: Whether to use OCR for PDFs.
        pdf_engine: pdf library to use for pdf generation.
    """
    input_path = Path(input_path)
    if input_path.is_file():
        text = extract_text_from_file(input_path, use_ocr)
        if text:
            if pdf_engine == 'fpdf':
                chunk_text_into_pdfs_fpdf(text, output_dir, pages_per_pdf, base_filename=input_path.stem)
            else:
                raise ValueError("FPDF library is not installed")
    elif input_path.is_dir():
        for file_path in tqdm(input_path.iterdir(), desc="Processing Files"):
            if file_path.is_file():
                text = extract_text_from_file(file_path, use_ocr)
                if text:
                    if pdf_engine == 'fpdf':
                        chunk_text_into_pdfs_fpdf(text, output_dir, pages_per_pdf, base_filename=file_path.stem)
                    else:
                        raise ValueError("FPDF library is not installed")
    else:
        logging.error("Input path is not a valid file or directory.")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Process files into text and chunk into PDFs.")
    parser.add_argument("input_path", help="Path to the input file or directory.")
    parser.add_argument(
        "--output_dir", help="Directory to save output PDF chunks.", default=script_dir
    )
    parser.add_argument(
        "--pages_per_pdf",
        type=int,
        help="Maximum number of pages per PDF.",
        default=500,
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Enable OCR for scanned PDFs (requires tesseract)",
    )
    parser.add_argument(
        "--pdf_engine",
        type=str,
        choices=["fpdf"],
        help="Type your pdf engine. [ fpdf]",
        default="fpdf",
    )

    args = parser.parse_args()

    process_files(
        args.input_path, args.output_dir, args.pages_per_pdf, args.ocr, args.pdf_engine
    )
    logging.info(f"Processed files. Check the '{args.output_dir}' directory for output.")
