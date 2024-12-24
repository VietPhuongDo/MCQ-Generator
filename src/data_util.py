from PyPDF2 import PdfReader
import io
from src.logger import logging


def read_input_file(file_content):
    try:
        # Convert binary content to file-like object
        file_obj = io.BytesIO(file_content)

        if file_content.startswith(b'%PDF'):
            pdf_reader = PdfReader(file_obj)
            return " ".join(page.extract_text() for page in pdf_reader.pages)

        else:
            return file_content.decode('utf-8')

    except Exception as e:
        logging.error(f"Error reading file: {str(e)}")
        raise Exception("Error processing file")