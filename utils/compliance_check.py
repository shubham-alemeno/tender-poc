import pandas as pd
from utils.markdown_utils_experimental import PDFMarkdown
from io import BytesIO, StringIO
from utils.llm_client import LLMClient
import time
from utils.system_prompt import compliance_check_system_prompt

class ComplianceChecker:
    def __init__(self) -> None:
        self.tender_markdown = None
        self.sotr_matrix_content = None

    def load_tender(self, tender_file_content: bytes) -> None:
        """
        Load tender data from a PDF file.
        """
        try:
            tender = PDFMarkdown()

            self.tender_markdown = tender.pdf_to_markdown(tender_file_content)
        
        except Exception as e:
            raise Exception(f"Error loading tender data: {str(e)}")

    def load_matrix(self, sotr_matrix_file_content: bytes) -> None:
        """
        Load compliance matrix from an xlsx file.
        """
        try:
            self.sotr_matrix_content = pd.read_excel(BytesIO(sotr_matrix_file_content))
        except Exception as e:
            raise Exception(f"Error loading SOTR matrix: {str(e)}")
    def check_compliance(self) -> pd.DataFrame:
        if self.tender_markdown is None or self.sotr_matrix_content is None:
            raise Exception("Tender document or SOTR matrix not loaded.")

        compliance_results = pd.DataFrame(columns=['Clause Number', 'Clause Text', 'Compliance Summary', 'Status'])
        compliance_checker_expert = LLMClient()

        for i in range(0, len(self.sotr_matrix_content), 10):
            rows = self.sotr_matrix_content.iloc[i:i+10]
            
            system_prompt = """
                You are a compliance analyst tasked with comparing a list of compliance clauses against extracted text from a tender document. For each clause, perform the following steps:

                Carefully read and analyze the clause text.
                Compare the clause requirements with the tender document text.
                Provide a concise compliance summary (max 50 words) stating whether the tender document meets, partially meets, or does not meet the clause requirements.
                Identify and extract the specific reference from the tender document that supports your compliance summary.
                Assign a status:

                "Yes" if fully compliant
                "Partial" if partially compliant
                "No" if not compliant



                Respond in CSV format using | as the separator, with the following columns:
                Clause Number|Clause Text|Compliance Summary|Status|Reference
                Ensure that any | characters within text fields are properly escaped or replaced with an appropriate alternative.
                Do not include any additional explanations or text outside of this CSV format. The first line of your response should be the CSV header, followed immediately by the data rows.
                Example input:
                Compliance clauses:

                "The supplier must provide 24/7 customer support."
                "All products must be delivered within 5 business days."

                Tender document text:
                "Our company offers customer support from 9 AM to 5 PM, Monday through Friday. We guarantee delivery of all products within 3-7 business days, depending on the customer's location."
                Example output:
                Clause Number|Clause Text|Compliance Summary|Status|Reference
                1|The supplier must provide 24/7 customer support.|Tender document states support is only available during limited hours on weekdays. Does not meet 24/7 requirement.|No|"Our company offers customer support from 9 AM to 5 PM, Monday through Friday."
                2|All products must be delivered within 5 business days.|Tender document guarantees delivery within 3-7 business days, which partially meets the requirement but may exceed 5 days.|Partial|"We guarantee delivery of all products within 3-7 business days, depending on the customer's location."
                Analyze the provided compliance clauses and tender document text, then generate the CSV output as described above.
            """
            user_prompt = f"Tender Document:\n{self.tender_markdown}\n\nClauses:\n" + "\n".join([f"{index}, {row['Clause']}" for index, row in rows.iterrows()])

            compliance_checker_expert_answers = compliance_checker_expert.call_llm(
                system_prompt=compliance_check_system_prompt,
                user_prompt=user_prompt
            )
            
            print(compliance_checker_expert_answers)

            try:
                parsed_answers = pd.read_csv(StringIO(compliance_checker_expert_answers), sep='|', quotechar='"', escapechar='\\')
            except pd.errors.ParserError:
                parsed_answers = self.parse_csv_manually(compliance_checker_expert_answers)

            required_columns = ['Clause Number', 'Clause Text', 'Compliance Summary', 'Status', 'Reference']
            for col in required_columns:
                if col not in parsed_answers.columns:
                    parsed_answers[col] = 'Unknown'

            compliance_results = pd.concat([compliance_results, parsed_answers[required_columns]], ignore_index=True)

        return compliance_results

    def parse_csv_manually(self, csv_string):
        lines = csv_string.strip().split('\n')
        data = []
        for line in lines[1:]:
            parts = line.split('|')
            if len(parts) != 5:
                data.append([None, None, None, None, None])
        
        return pd.DataFrame(data, columns=['Clause Number', 'Clause Text', 'Compliance Summary', 'Status', 'Reference'])
