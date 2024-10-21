import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

import pypdfium2 as pdfium
from PIL import Image
from marker.utils import flush_cuda_memory
from marker.tables.table import format_tables
from marker.debug.data import dump_bbox_debug_data
from marker.layout.layout import surya_layout, annotate_block_types
from marker.layout.order import surya_order, sort_blocks_in_reading_order
from marker.ocr.lang import replace_langs_with_codes, validate_langs
from marker.ocr.detection import surya_detection
from marker.ocr.recognition import run_ocr
from marker.pdf.extract_text import get_text_blocks
from marker.cleaners.headers import filter_header_footer, filter_common_titles
from marker.equations.equations import replace_equations
from marker.pdf.utils import find_filetype
from marker.postprocessors.editor import edit_full_text
from marker.cleaners.code import identify_code_blocks, indent_blocks
from marker.cleaners.bullets import replace_bullets
from marker.cleaners.headings import split_heading_blocks
from marker.cleaners.fontstyle import find_bold_italic
from marker.postprocessors.markdown import merge_spans, merge_lines, get_full_text
from marker.cleaners.text import cleanup_text
from marker.images.extract import extract_images
from marker.images.save import images_to_dict
from marker.models import load_all_models
from typing import List, Dict, Tuple, Optional
from marker.settings import settings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from functools import lru_cache
import tempfile
import time
import uuid
import datetime

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_marker_models():
    return load_all_models()

class PDFMarkdown:
    def __init__(self, pdf_path=None, file_id=None):
        self.pdf_path = pdf_path
        self.markdown_text = None
        self.markdown_file_path = None
        self.file_id = file_id

    def pdf_to_markdown(self, file_content, progress_callback=None):
        """Convert PDF content to Markdown using marker-pdf library and save to a file."""
        logger.info("Starting PDF to Markdown conversion")
        model_lst = get_marker_models()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
            logger.info(f"Temporary file created: {temp_file_path}")
    
        try:
            logger.info("Beginning conversion process")
            full_text, doc_images, out_meta = self.convert_single_pdf(
                fname=temp_file_path,
                model_lst=model_lst,
                batch_multiplier=3,
                progress_callback=progress_callback
            )
            logger.info("Conversion process completed")
            
            if not full_text:
                logger.error("Conversion resulted in empty text")
                raise ValueError("Conversion resulted in empty text")
            
            self.markdown_text = full_text
            
            # Save the markdown text to a file
            unique_id = str(uuid.uuid4())[:8]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tender_{timestamp}_{unique_id}.md"
            
            # Ensure the tender_data directory exists
            os.makedirs("tender_data", exist_ok=True)
            
            file_path = os.path.join("tender_data", filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.markdown_text)
            
            logger.info(f"Markdown file saved: {file_path}")
            self.markdown_file_path = file_path
            
            if progress_callback:
                progress_callback(1.0, "Conversion complete and file saved")
            
            return self.markdown_text
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}", exc_info=True)
            raise
        finally:
            temp_file.close()            
            time.sleep(0.1)           
            try:
                os.unlink(temp_file_path)
                logger.info(f"Temporary file deleted: {temp_file_path}")
            except PermissionError:
                logger.warning(f"Could not delete temporary file: {temp_file_path}")



    def convert_single_pdf(self, fname: str, model_lst: List, max_pages: int = None,
                       start_page: int = None, metadata: Optional[Dict] = None,
                       langs: Optional[List[str]] = None, batch_multiplier: int = 1,
                       ocr_all_pages: bool = False, progress_callback=None) -> Tuple[str, Dict[str, Image.Image], Dict]:
        total_steps = 11
        current_step = 0

        def update_progress(step_name):
            nonlocal current_step
            current_step += 1
            logger.info(f"Step {current_step}/{total_steps}: {step_name}")
            if progress_callback:
                progress_callback((current_step / total_steps) * 100, step_name)

        try:
            logger.info(f"Starting conversion of PDF: {fname}")
            print(f"Starting conversion of PDF: {fname}")
            ocr_all_pages = ocr_all_pages or settings.OCR_ALL_PAGES
            langs = metadata.get("languages", langs) if metadata else langs
            langs = replace_langs_with_codes(langs)
            validate_langs(langs)
            print(f"Languages: {langs}")
    
            filetype = find_filetype(fname)
            print(f"File type: {filetype}")
            out_meta = {"languages": langs, "filetype": filetype}
            if filetype == "other":
                print("Unsupported file type. Aborting.")
                return "", {}, out_meta
    
            doc = pdfium.PdfDocument(fname)
            try:
                pages, toc = get_text_blocks(doc, fname, max_pages=max_pages, start_page=start_page)
                update_progress("Extracted text blocks")
                print(f"Extracted {len(pages)} pages")
    
                out_meta.update({"toc": toc, "pages": len(pages)})
    
                if start_page:
                    for _ in range(start_page):
                        doc.del_page(0)
                    print(f"Adjusted start page to {start_page}")
    
                texify_model, layout_model, order_model, edit_model, detection_model, ocr_model = model_lst
                print("Models loaded successfully")
    
                surya_detection(doc, pages, detection_model, batch_multiplier=batch_multiplier)
                flush_cuda_memory()
                update_progress("Detected text lines")
    
                pages, ocr_stats = run_ocr(doc, pages, langs, ocr_model, batch_multiplier=batch_multiplier, ocr_all_pages=ocr_all_pages)
                flush_cuda_memory()
                update_progress("Performed OCR")
                print(f"OCR stats: {ocr_stats}")
    
                out_meta["ocr_stats"] = ocr_stats
                if not any(page.blocks for page in pages):
                    print(f"Could not extract any text blocks for {fname}")
                    return "", {}, out_meta
    
                surya_layout(doc, pages, layout_model, batch_multiplier=batch_multiplier)
                flush_cuda_memory()
                update_progress("Analyzed layout")
    
                bad_span_ids = filter_header_footer(pages)
                out_meta["block_stats"] = {"header_footer": len(bad_span_ids)}
                print(f"Filtered {len(bad_span_ids)} header/footer spans")
                annotate_block_types(pages)
                dump_bbox_debug_data(doc, fname, pages)
                update_progress("Filtered headers and footers")
    
                surya_order(doc, pages, order_model, batch_multiplier=batch_multiplier)
                sort_blocks_in_reading_order(pages)
                flush_cuda_memory()
                update_progress("Determined reading order")
    
                code_block_count = identify_code_blocks(pages)
                out_meta["block_stats"]["code"] = code_block_count
                indent_blocks(pages)
                update_progress("Processed code blocks")
                print(f"Identified {code_block_count} code blocks")
    
                table_count = format_tables(pages)
                out_meta["block_stats"]["table"] = table_count
                print(f"Formatted {table_count} tables")
    
                for page in pages:
                    for block in page.blocks:
                        block.filter_spans(bad_span_ids)
                        block.filter_bad_span_types()
    
                filtered, eq_stats = replace_equations(doc, pages, texify_model, batch_multiplier=batch_multiplier)
                flush_cuda_memory()
                out_meta["block_stats"]["equations"] = eq_stats
                update_progress("Processed equations")
                print(f"Equation stats: {eq_stats}")
    
                if settings.EXTRACT_IMAGES:
                    extract_images(doc, pages)
                update_progress("Extracted images")
    
                split_heading_blocks(pages)
                find_bold_italic(pages)
                merged_lines = merge_spans(filtered)
                text_blocks = merge_lines(merged_lines)
                text_blocks = filter_common_titles(text_blocks)
                
                page_separated_text = []
                for i, page in enumerate(pages, start=1):
                    page_text = ""
                    for block in page.blocks:
                        if hasattr(block, 'text'):
                            page_text += block.text
                        else:
                            print(f"Warning: Block on page {i} has no 'text' attribute")
                            print(f"Block attributes: {dir(block)}")
                    page_text = cleanup_text(page_text)
                    page_separated_text.append(f"{page_text}\n\n---\nPage {i}\n---\n\n")
                    print(f"Processed page {i}: {len(page_text)} characters")
    
                full_text = "".join(page_separated_text)
                update_progress("Formatted text")
    
                full_text, edit_stats = edit_full_text(full_text, edit_model, batch_multiplier=batch_multiplier)
                flush_cuda_memory()
                out_meta["postprocess_stats"] = {"edit": edit_stats}
                doc_images = images_to_dict(pages)
                update_progress("Finalized document")
                print(f"Final document length: {len(full_text)} characters")
                print(f"Edit stats: {edit_stats}")
    
                return full_text, doc_images, out_meta
            finally:
                doc.close()
    
        except Exception as e:
            logger.error(f"Error in convert_single_pdf: {str(e)}", exc_info=True)
            raise

        finally:
            logger.info("Conversion process finished")


    def save_markdown_to_file(self, file_path, output_name):
        output_path = f"{file_path}/{output_name}.md"
        self.markdown_file_path = output_path
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(self.markdown_text)
        return self.markdown_file_path

    def split_markdown_by_headers(self):
        if self.markdown_text is None:
            raise Exception("please convert to markdown first using pdf_to_markdown()")
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(self.markdown_text)
        return md_header_splits

    def get_file_id(self):
        return self.file_id
    
    def load_from_pdf(self, file_content, file_id):
        self.file_id = file_id
        self.markdown_text = self.pdf_to_markdown(file_content)
        return self.markdown_text

    def get_markdown_text(self):
        return self.markdown_text

    def get_markdown_file_path(self):
        return self.markdown_file_path

    def extract_sections(self, headers_to_extract=None):
        if self.markdown_text is None:
            raise Exception("Please convert to markdown first using pdf_to_markdown()")
        
        if headers_to_extract is None:
            headers_to_extract = ["#", "##", "###"]
        
        sections = {}
        current_section = None
        current_content = []

        for line in self.markdown_text.split('\n'):
            if any(line.startswith(header) for header in headers_to_extract):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def search_markdown(self, query):
        if self.markdown_text is None:
            raise Exception("Please convert to markdown first using pdf_to_markdown()")
        
        lines = self.markdown_text.split('\n')
        results = []
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                results.append({
                    'line_number': i + 1,
                    'content': line,
                    'context': context
                })
        return results

    def get_table_of_contents(self):
        if self.markdown_text is None:
            raise Exception("Please convert to markdown first using pdf_to_markdown()")
        
        toc = []
        for line in self.markdown_text.split('\n'):
            if line.startswith('#'):
                level = line.count('#')
                title = line.strip('#').strip()
                toc.append((level, title))
        return toc

    def __str__(self):
        return f"PDFMarkdown(file_id={self.file_id}, pdf_path={self.pdf_path})"

    def __repr__(self):
        return self.__str__()