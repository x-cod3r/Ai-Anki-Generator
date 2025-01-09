# workflow_utils.py
import os
import io
from pathlib import Path
from fpdf import FPDF
import requests
from tqdm import tqdm
import logging
try:
  from PIL import Image
except ImportError:
  pass
try:
  import pytesseract
except ImportError:
  pass
try:
  from docx import Document
except ImportError:
  pass
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


        
def extract_text_from_pdf_pypdf(pdf_path):
    text = ""
    try:
      reader = PdfReader(pdf_path)
      for page in reader.pages:
          text += page.extract_text()
    except Exception as e:
        logging.error(f"Error while extracting text using pypdf with {pdf_path}: {e}")
        return None
    return text.strip()

def extract_text_from_docx(docx_path):
    text = ""
    try:
        doc = Document(docx_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logging.error(f"Error while extracting text from docx with {docx_path}: {e}")
        return None
    return text.strip()

def extract_text_from_txt(txt_path):
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        logging.error(f"Error while extracting text from txt with {txt_path}: {e}")
        return None
    return text.strip()

def extract_text_from_file(file_path, use_ocr=False):
    """
    Extracts text from various file types (PDF, DOCX, TXT, etc.).

    Args:
        file_path: Path to the file.
        use_ocr: Boolean, whether to use OCR for PDFs if text extraction fails.

    Returns:
        The extracted text as a string, or None if extraction fails.
    """
    file_path = Path(file_path)
    logging.info(f"Extracting text from: {file_path}")
    try:
        if file_path.suffix.lower() == ".pdf":
           text = extract_text_from_pdf_pypdf(str(file_path))
           if not text and use_ocr:
              logging.info(f"No text found in PDF, attempting OCR: {file_path}")
              try:
                  reader = PdfReader(file_path)
                  text = ""
                  for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        image = page.to_image()
                        image_bytes = io.BytesIO()
                        image.save(image_bytes, format="PNG")
                        image_bytes.seek(0)
                        pil_image = Image.open(image_bytes)
                        text += pytesseract.image_to_string(pil_image)
              except Exception as e:
                   logging.error(f"OCR failed for {file_path} with error: {e}")
              if not text.strip():
                   logging.warning(f"Failed to extract text from {file_path} using both methods.")
                   return None

           elif not text:
              logging.warning(f"Failed to extract text from {file_path} using pypdf.")
              return None
        elif file_path.suffix.lower() == ".docx":
             text = extract_text_from_docx(str(file_path))
             if not text:
               logging.warning(f"Failed to extract text from {file_path} using docx.")
               return None
        elif file_path.suffix.lower() == ".txt":
             text = extract_text_from_txt(str(file_path))
             if not text:
               logging.warning(f"Failed to extract text from {file_path} using txt.")
               return None
        else:
            logging.warning(f"Unsupported file type {file_path.suffix}")
            return None

        # Start of debugging for character
        text = text.replace(chr(64257), 'fi') # replace the ligature fi
        text = text.replace(chr(64258), 'fl') # replace the ligature fl
        text = text.replace(chr(64256), 'ff') # replace the ligature ff        
        #text = text.replace(chr(U+FB01), 'fi') # replace the ligature fi
        text = text.replace("\ufb01", 'fi') # replace the ligature fi
        # End of debug for characters
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
        download_DejaVu_if_not_exists("DejaVuSans.ttf", "https://github.com/x-cod3r/MYSOFTWARES/raw/refs/heads/main/DejaVuSans.ttf")
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
    try:
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
    except Exception as e:
       logging.error(f"Error in process files: {e}")

# workflow_utils.py
import os
os.environ["GRPC_VERBOSITY"] = "NONE"
import google.generativeai as genai
import logging
import pypdf

#genai.configure(api_key="innfvpiwmerpgvmpewrogv52re84gvenewofun")
#model = genai.GenerativeModel("gemini-2.0-flash-exp")

def extract_text_from_pdf_no_ocr(pdf_file):
    logging.info(f"Extracting text from PDF: {pdf_file}")
    try:
        with open(pdf_file, 'rb') as file:
            reader = pypdf.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        logging.info(f"Text extracted successfully.")
        return text
    except FileNotFoundError as e:
        logging.error(f"Error: File not found: {pdf_file}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error while extracting text from {pdf_file}: {e}")
        return None

def generate_response(prompt, pdf_text=None, model = None):
    if pdf_text:
        prompt = f"{prompt}\n\nPDF Content:\n{pdf_text}"
    
    response = model.generate_content(prompt)
    return response.text

def save_response_to_file(response_text, filename):
    with open(filename, "a", encoding="utf-8") as file:  # Changed 'w' to 'a' for append mode
        file.write(response_text)
        file.write("\n")  # Add a newline to separate responses
        logging.info(f"Flashcards have been appended to '{filename}'.")

def chat_with_pdf(prompt, pdf_text, model):
    
    response_text = generate_response(prompt, pdf_text,model)
    return response_text

import genanki
import os
import random

def create_anki_deck(filename, output_path):
    """
    Creates an Anki deck from a text file.
    Parses the file line by line, looking for 'front' or 'Front'
    followed by a colon, then 'back' or 'Back' followed by a colon.
    If the colon is missing, use the rest of the line.
    Skips cards without both a valid front and back.
    """

    notes = []
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
        return

    front_content = None
    back_content = None

    for line in lines:
        line = line.strip()
        if line.lower().startswith("front"):
            if front_content is not None and back_content is not None:
                # A full card is ready, save it.
                notes.append((front_content, back_content))

            front_content = ""
            if line.lower() == "front":
                 front_content = ""
            elif line.lower().startswith("front:"):
                front_content = line[len("front:"):].strip()
            else:
                 front_content = line[len("front"):].strip()
            back_content = None  # Reset back content
        elif line.lower().startswith("back"):
            if front_content is None:
                continue # If we do not have a front do not continue.

            back_content = ""
            if line.lower() == "back":
                 back_content = ""
            elif line.lower().startswith("back:"):
                back_content = line[len("back:"):].strip()
            else:
                 back_content = line[len("back"):].strip()
            if front_content and back_content:
                # Only save the card if we have both a front and a back
                notes.append((front_content, back_content))
                front_content = None
                back_content = None
            else:
                 front_content = None
                 back_content = None # reset front and back if it was invalid.
    if front_content is not None and back_content is not None:
         # Handle the case if the last card has both front and back
         notes.append((front_content, back_content))

    if not notes:
        print(f"No valid notes found in: {filename}")
        return

    # Generate random IDs
    model_id = random.randrange(1 << 30, 1 << 31)
    deck_id = random.randrange(1 << 30, 1 << 31)

    model = genanki.Model(
        model_id,
        'Styled Simple Model',
        fields=[
            {'name': 'Front'},
            {'name': 'Back'},
        ],
        templates=[
            {
                'name': 'Card 1',
                 'qfmt': '<div style="text-align: center; font-size: 1.3em;"><b>{{Front}}</b></div>',
                'afmt': '<div style="text-align: center; font-size: 1.3em;">{{Front}}</div><br><div style="text-align: center; font-size: 1.3em;">{{Back}}</div>',
            },
        ],
    )
    my_deck = genanki.Deck(deck_id, 'Test Deck first')

    for front, back in notes:
        my_note = genanki.Note(
            model=model,
            fields=[front, back],
        )
        my_deck.add_note(my_note)

    package = genanki.Package(my_deck)
    try:
        package.write_to_file(output_path)
    except Exception as e:
        print(f"Error writing Anki package to {output_path}: {e}")
        return
    logging.info(f"Anki package created successfully: {output_path}")