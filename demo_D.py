import streamlit as st
from utils.sotr_construction import SOTRMarkdown
from utils.llm_client import LLMClient
from utils.bid_document import BidDocument
from dotenv import load_dotenv
import os
import pandas as pd
import json

def main():
    st.title("Tender-POC Demo Application")

    load_dotenv()

    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    model = os.getenv("MODEL")

    llm_client = LLMClient(project_id=project_id, location=location, model=model)

    st.header("Tender Document Upload")
    tender_file = st.file_uploader("Upload Tender Document (SOTR)", type=["pdf"])
    if tender_file is not None:
        st.success("Tender document uploaded successfully!")
        
        if st.button("Process Tender Document"):
            try:
                sotr = SOTRMarkdown(llm_client=llm_client)
                sotr.load_from_pdf(tender_file, "tender_file_id")
                
                st.success("Tender document processed successfully!")

                split_text = sotr.get_matrix_points()

                cleaned_csv_data = [["Sr. No.", "Clause", "Clause Reference"]]
                for i, row in enumerate(split_text[1:], start=1):
                    items = row.split("|")
                    cleaned_csv_data.append([i, items[1].replace('"', ''), items[2]])

                df = pd.DataFrame(cleaned_csv_data[1:], columns=cleaned_csv_data[0])
                
                st.subheader("Compliance Matrix")
                st.dataframe(df)

                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download Compliance Matrix as CSV",
                    data=csv,
                    file_name="compliance_matrix.csv",
                    mime="text/csv"
                )

                st.session_state['compliance_matrix'] = df

            except Exception as e:
                st.error(f"An error occurred while processing the tender document: {str(e)}")

    st.header("Bid Document Upload")
    bid_file = st.file_uploader("Upload Bid Document", type=["pdf"])
    if bid_file is not None:
        st.success("Bid document uploaded successfully!")
        
        if st.button("Process Bid Document and Check Compliance"):
            try:
                bid_doc = BidDocument(bid_file, "unique_file_id")
                st.success("Bid document processed successfully!")

                if 'compliance_matrix' in st.session_state:
                    compliance_matrix = st.session_state['compliance_matrix']
                    
                    system_prompt = f"""
                    You are a compliance checker. You will be provided with a compliance matrix and the content of a bid document.
                    Your task is to check if the bid document complies with each requirement in the compliance matrix.
                    Provide a brief explanation for each compliance check.

                    Compliance Matrix:
                    {compliance_matrix.to_string(index=False)}

                    Bid Document Content:
                    {bid_doc.content}

                    For each requirement in the compliance matrix, determine if the bid document complies and provide a brief explanation.
                    Format your response as a JSON array of objects, where each object has the following structure:
                    {{
                        "requirement": "The requirement text",
                        "compliant": true/false,
                        "explanation": "Your brief explanation"
                    }}
                    """

                    user_prompt = "Perform the compliance check and provide the results in the specified JSON format."

                    response = llm_client.call_llm(system_prompt, user_prompt)

                    compliance_results = json.loads(response)
                    results_df = pd.DataFrame(compliance_results)

                    st.subheader("Compliance Check Results")
                    st.dataframe(results_df)

                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="Download Compliance Check Results as CSV",
                        data=csv,
                        file_name="compliance_check_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("Please process the tender document first to generate the compliance matrix.")

            except Exception as e:
                st.error(f"An error occurred while processing the bid document: {str(e)}")

if __name__ == "__main__":
    main()