import os
from utils.markdown_utils import PDFMarkdown

def get_file_path(is_pdf: bool = False) -> str:
    """Prompt user for file path and validate its existence."""
    file_type = "PDF" if is_pdf else "Markdown"
    while True:
        file_path = input(f"Enter the path to the {file_type} file: ")
        if os.path.exists(file_path):
            return file_path
        print(f"File not found. Please enter a valid {file_type} file path.")

def process_file(file_path: str, is_pdf: bool) -> str:
    """Process the input file and return its content."""
    file_name = os.path.basename(file_path)
    print(f"Processing file: {file_name}")
    
    if is_pdf:
        pdf_markdown = PDFMarkdown(file_path)
        content = pdf_markdown.pdf_to_markdown()
    else:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    
    print("File content preview:")
    print("\n".join(content.split("\n")[:3]))
    return content