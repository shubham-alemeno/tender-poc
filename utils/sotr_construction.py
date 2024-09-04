from utils.markdown_utils import PDFMarkdown
from utils.llm_client import LLMClient
import pandas as pd


class SOTRMarkdown(PDFMarkdown):

    def __init__(self,llm_client):
        self.markdown_sections=[]
        self.sotr_matrix=[]
        self.llm_client=llm_client
        self.df=None

    def load_from_md(self,file_path,file_id):
        self.file_id=file_id
        with open(file_path,"r") as file:
            self.markdown_text=file.read()
        return self.markdown_text


    def load_from_pdf(self,file_path,file_id):
         self.file_id=file_id    
         self.pdf_path=file_path
         self.pdf_to_markdown()
         return self.markdown_text


    def post_process_response(self,split_text):
        headers=["Sr. No.","Clause","Clause Reference"]
        cleaned_csv_data=[]
        for i,row in enumerate(split_text[1:]):
            items=row.split("|")
            cleaned_csv_data.append([i,items[1].replace('"',''),items[2]])
        df=pd.DataFrame(columns=headers,data=cleaned_csv_data)
        return df

    def get_matrix_points(self):
        points=['Sr. No.,Requirement(clause content),Source Reference(reference number of clause in the document)']
        if(self.markdown_text):
            markdown_text_splits=self.split_markdown_by_headers()
            print(markdown_text_splits)
            cleaned_text_splits=[]
            for point in markdown_text_splits:
                section_header=point.metadata["Header 2"]
                section_no=section_header.split(" ")[0]
                if point.page_content.strip():
                    cleaned_text_splits.append({"section":section_no,"content":point.page_content})
                
            self.markdown_sections=cleaned_text_splits
            print(cleaned_text_splits)
            system_prompt="""
                    Given a part of a specific document in markdown format containing compliance requirements and the section number of the part, create a comprehensive compliance matrix following these steps:

                        1. Document Analysis:
                        - Thoroughly review the provided document.
                        - Identify all sections that contain compliance requirements or standards.
                        - Note any existing structure or categorization within the document.

                        2. Requirement Extraction:
                        - Extract each individual requirement or standard from the document.
                        - Maintain the original wording of each requirement.
                        - Preserve any numbering or referencing system used in the document.
                        - prefix the section number to the clause reference.
                        - if there is a table , use the same clause reference for all rows.

                        3. Identify Key Information:
                        - For each requirement, identify key pieces of information such as:
                            - Any unique identifiers or reference numbers
                            - The specific section or clause where the requirement is found
                            - Any specified deadlines or timeframes
                            - Particular actions or evidence required for compliance
                            - Responsible parties or roles mentioned
                            - Any associated penalties or consequences for non-compliance
                        - Note any other recurring or important information types specific to this document
                        - Do not change the structure or content of the clause , just add it verbatim as a compliance clause 
                        
                        4. Column Definition:
                        - Use the following fixed columns for the matrix:
                            a. Sr. No.
                            b. Requirement (clause content)
                            c. Source Reference (reference number of clause in the document)

                        5. Matrix Structure:
                        - Create a table with the defined columns.
                        - Use the pipe character (|) as the separator for the CSV format.

                        6. Populating the Matrix:
                        - Enter each requirement as a separate row in the matrix.
                        - Fill in all relevant columns for each requirement.
                        - Use the exact language from the source document for the requirement text.
                        - If certain information is not explicitly stated in the document, mark it as "Not Specified" or "To Be Determined" rather than leaving it blank.

                        7. Maintaining Document Integrity:
                        - Preserve any hierarchical structure present in the original document (e.g., main sections, subsections).

                        8. Consistency and Clarity:
                        - Use consistent terminology and formatting throughout the matrix.
                        - Ensure that each cell contains clear, specific information.
                        - Avoid summarizing or paraphrasing the requirements.

                        9. Review and Refinement:
                        - After initial creation, review the matrix to ensure all requirements are captured accurately.

                        10. Versioning and Updates:
                        - Prepare the matrix in a format that allows for easy updates and tracking of changes over time.

                        Follow these steps to create a compliance matrix that accurately reflects the structure and content of the provided document, ensuring no information is omitted or summarized.
                        Return only the compliance matrix in CSV format with pipe (|) as the separator and no other text along with it. The CSV should have the following header:

                        Sr. No.|Requirement (clause content)|Source Reference (reference number of clause in the document)
            """
            for i,text_block in enumerate(cleaned_text_splits):
                user_prompt=f"""
                section number:
                {text_block["section"]}
                markdown text:
                {text_block["content"]}
                """
                response=self.llm_client.call_llm(system_prompt=system_prompt,user_prompt=user_prompt,max_tokens=8192)
                if response is None:
                    raise Exception("Error Occured while calling LLM")
                split_points=response.split("\n")
                points.extend(split_points[1:])
                print(f"completed {i+1}/{len(cleaned_text_splits)}")
            self.sotr_matrix=points
            self.df=self.post_process_response(points)
            return self.df,points


        else:
            raise Exception("self.markdown_text is None. Please convert file to markdown first using pdf_to_markdown()")
