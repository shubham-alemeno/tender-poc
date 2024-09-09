from utils.markdown_utils import PDFMarkdown
from utils.llm_client import LLMClient
import pandas as pd
from utils.system_prompt import system_prompt as system_prompt_text


class SOTRMarkdown(PDFMarkdown):

    def __init__(self, llm_client):
        self.markdown_sections = []
        self.sotr_matrix = []
        self.llm_client = llm_client
        self.df = None

    def load_from_md(self, file_content, file_id):
        self.file_id = file_id
        self.markdown_text = file_content
        return self.markdown_text

    def load_from_pdf(self, file_content, file_id):
        self.file_id = file_id    
        self.pdf_path = None  # or handle this differently if needed
        self.markdown_text = self.pdf_to_markdown(file_content)
        return self.markdown_text

    def post_process_response(self, split_text):
        headers = ["Sr. No.", "Clause", "Clause Reference"]
        cleaned_csv_data = []
        for i, row in enumerate(split_text[1:]):
            items = row.split("|")
            cleaned_csv_data.append([i, items[1].replace('"', ''), items[2]])
        df = pd.DataFrame(columns=headers, data=cleaned_csv_data)
        return df

    def get_matrix_points(self):
        points = ['Sr. No.,Requirement(clause content),Source Reference(reference number of clause in the document)']
        if self.markdown_text:
            markdown_text_splits = self.split_markdown_by_headers()
            print(markdown_text_splits)
            cleaned_text_splits = []
            for point in markdown_text_splits:
                section_header = point.metadata["Header 2"]
                section_no = section_header.split(" ")[0]
                if point.page_content.strip():
                    cleaned_text_splits.append({"section": section_no, "content": point.page_content})
            
            self.markdown_sections = cleaned_text_splits
            print(cleaned_text_splits)

            for i, text_block in enumerate(cleaned_text_splits):
                user_prompt = f"""
                section number:
                {text_block["section"]}
                markdown text:
                {text_block["content"]}
                """
                try:
                    response = self.llm_client.call_llm(system_prompt = system_prompt_text, user_prompt = user_prompt, max_tokens = 8192)
                    if response is None:
                        print(f"Warning: LLM returned None for section {text_block['section']}. Skipping this section.")
                        continue
                    split_points = response.split("\n")
                    points.extend(split_points[1:])
                    print(f"completed {i+1}/{len(cleaned_text_splits)}")
                except Exception as e:
                    print(f"Error processing section {text_block['section']}: {str(e)}")

            self.sotr_matrix = points
            self.df = self.post_process_response(points)
            return self.df, points
        else:
            raise Exception("self.markdown_text is None. Please convert file to markdown first using pdf_to_markdown()")