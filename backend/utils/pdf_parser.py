import PyPDF2

def parse_pdf(file_path):
    """
    Extracts text from a PDF file.
    """
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"Error parsing PDF: {str(e)}")
    return text
