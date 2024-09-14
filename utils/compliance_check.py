import pandas as pd
from utils.markdown_utils_experimental import PDFMarkdown
from io import BytesIO, StringIO
from utils.llm_client import LLMClient

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
                system_prompt=system_prompt,
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

    # Original version working for small
    # def check_compliance(self) -> pd.DataFrame:
    #     if self.tender_markdown is None or self.sotr_matrix_content is None:
    #         raise Exception("Tender document or SOTR matrix not loaded.")

    #     compliance_results = pd.DataFrame(columns=['Clause Number', 'Clause Text', 'Compliance Summary', 'Status'])
    #     compliance_checker_expert = LLMClient()

    #     for i in range(0, len(self.sotr_matrix_content), 10):
    #         rows = self.sotr_matrix_content.iloc[i:i+10]
            
    #         system_prompt = """
    #         For each clause in the given list:

    #         1. Carefully read and analyze the clause text.
    #         2. Compare the clause requirements with the tender document specifications.
    #         3. Provide a concise compliance summary (max 50 words) stating whether the tender document meets, partially meets, or does not meet the clause requirements.
    #         4. Assign a status:
    #            - "Yes" if fully compliant
    #            - "Partial" if partially compliant
    #            - "No" if not compliant

    #         Respond in CSV format with the following columns:
    #         Clause Number, Clause Text, Compliance Summary, Status

    #         Ensure that commas within text fields are properly escaped or enclosed in quotes.
    #         Do not include any additional explanations or code outside of this CSV format.
    #         """
    #         user_prompt = f"Tender Document:\n{self.tender_markdown}\n\nClauses:\n" + "\n".join([f"{index}, {row['Clause']}" for index, row in rows.iterrows()])

    #         compliance_checker_expert_answers = compliance_checker_expert.call_llm(
    #             system_prompt=system_prompt,
    #             user_prompt=user_prompt
    #         )

    #         try:
    #             parsed_answers = pd.read_csv(StringIO(compliance_checker_expert_answers), quotechar='"', escapechar='\\')
    #         except pd.errors.ParserError:
    #             parsed_answers = pd.read_csv(StringIO(compliance_checker_expert_answers), quotechar='"', escapechar='\\', sep=',', engine='python')

    #         required_columns = ['Clause Number', 'Clause Text', 'Compliance Summary', 'Status']
    #         for col in required_columns:
    #             if col not in parsed_answers.columns:
    #                 parsed_answers[col] = 'Unknown'

    #         compliance_results = pd.concat([compliance_results, parsed_answers[required_columns]], ignore_index=True)

    #     return compliance_results

# CHUNCK Version    
# def check_compliance(self) -> pd.DataFrame:
#     if self.tender_markdown is None or self.sotr_matrix_content is None:
#         raise Exception("Tender document or SOTR matrix not loaded.")

#     compliance_results = []
#     compliance_checker_expert = LLMClient()

#     # Chunk the tender document
#     tender_chunks = self.chunk_document(self.tender_markdown, 2000)

#     for i, row in self.sotr_matrix_content.iterrows():
#         clause_number = row['Sr. No.']
#         clause_text = row['Clause']

#         system_prompt = f"""
#         Analyze the following clause against the tender document chunks:
#         Clause Number: {clause_number}
#         Clause Text: {clause_text}

#         Provide a concise compliance summary (max 50 words) and assign a status:
#         - "Yes" if fully compliant
#         - "Partial" if partially compliant
#         - "No" if not compliant
#         - "Unknown" if there's insufficient information

#         Respond in the following format:
#         Compliance Summary: [Your summary here]
#         Status: [Yes/Partial/No/Unknown]
#         """

#         user_prompt = "\n\n".join(tender_chunks)

#         max_retries = 3
#         for attempt in range(max_retries):
#             try:
#                 response = compliance_checker_expert.call_llm(
#                     system_prompt=system_prompt,
#                     user_prompt=user_prompt
#                 )
                
#                 summary, status = self.parse_llm_response(response)
                
#                 compliance_results.append({
#                     'Clause Number': clause_number,
#                     'Clause Text': clause_text,
#                     'Compliance Summary': summary,
#                     'Status': status
#                 })
#                 break
#             except Exception as e:
#                 if attempt == max_retries - 1:
#                     print(f"Failed to process clause {clause_number} after {max_retries} attempts.")
#                     compliance_results.append({
#                         'Clause Number': clause_number,
#                         'Clause Text': clause_text,
#                         'Compliance Summary': "Error in processing",
#                         'Status': "Unknown"
#                     })
#                 else:
#                     print(f"Retrying clause {clause_number} (attempt {attempt + 1})")

#     return pd.DataFrame(compliance_results)

# def chunk_document(self, document, chunk_size):
#     return [document[i:i+chunk_size] for i in range(0, len(document), chunk_size)]

# def parse_llm_response(self, response):
#     lines = response.strip().split('\n')
#     summary = ""
#     status = "Unknown"
#     for line in lines:
#         if line.startswith("Compliance Summary:"):
#             summary = line.split(":", 1)[1].strip()
#         elif line.startswith("Status:"):
#             status = line.split(":", 1)[1].strip()
#     return summary, status