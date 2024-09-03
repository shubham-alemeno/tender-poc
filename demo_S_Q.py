import streamlit as st
from utils.sotr_construction import SOTRMarkdown
from utils.llm_client import LLMClient
from utils.bid_document import BidDocument
from dotenv import load_dotenv
import os
import pandas as pd

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
                    questions = [f"Does the bid document comply with the following requirement: {row['Clause']}? Provide a brief explanation." for _, row in compliance_matrix.iterrows()]

                    compliance_results = []
                    for question in questions:
                        response = bid_doc.query(question)
                        compliance_results.append(response)

                    results_df = pd.DataFrame({
                        'Requirement': compliance_matrix['Clause'],
                        'Compliance Check': compliance_results
                    })

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