from PyPDF2 import PdfReader
from docx import Document
import io
from src.logger import logging


def read_input_file(file_content):
    try:
        # Convert binary content to file-like object
        file_obj = io.BytesIO(file_content)

        # Check if the file is a PDF
        if file_content.startswith(b'%PDF'):
            pdf_reader = PdfReader(file_obj)
            return " ".join(page.extract_text() for page in pdf_reader.pages)

        # Check if the file is a DOCX (by magic number)
        elif file_content.startswith(b'\x50\x4b\x03\x04'):  # DOCX magic number
            doc = Document(file_obj)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)

        # Assume the file is plain text
        else:
            return file_content.decode('utf-8')

    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        raise Exception("Error processing file")
