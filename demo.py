import streamlit as st
import logging
from utils.llm_client import LLMClient
from utils.sotr_construction import SOTRMarkdown
from utils.markdown_utils import PDFMarkdown
import os
import tempfile
import io
import pandas as pd

@st.cache_data
def load_env_vars():
    return {
        "project_id": os.getenv("PROJECT_ID"),
        "location": os.getenv("LOCATION"),
        "model": os.getenv("MODEL")
    }

@st.cache_resource
def get_llm_client(env_vars):
    return LLMClient(**env_vars)

def sotr_processing_tab(llm_client):
    st.subheader("SOTR Processing")
    st.write("This tab will contain the SOTR processing functionality.")

    sotr_file = st.file_uploader("Upload SOTR Document", type=["pdf"])

    if sotr_file is not None:
        st.write("SOTR document uploaded successfully!")

        try:
            progress_text = "Processing SOTR document. Please wait."
            my_bar = st.progress(0, text=progress_text)

            file_content = sotr_file.read()
            file_id = f"sotr_{sotr_file.name}"
            sotr = SOTRMarkdown(llm_client=llm_client)
            
            my_bar.progress(25, text=progress_text)
            
            sotr.load_from_pdf(file_content, file_id)
            
            my_bar.progress(50, text=progress_text)
            
            df, split_text = sotr.get_matrix_points()
            
            my_bar.progress(75, text=progress_text)
            
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Download Current Result",
                data=excel_data,
                file_name="sotr_matrix.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            my_bar.progress(100, text="Processing complete!")
            
            st.success("SOTR document processed successfully!")
        except Exception as e:
            st.error(f"Error processing SOTR document: {str(e)}")

def tender_qa_tab(llm_client):
    st.subheader("Tender Q&A")
    tender_pdf = st.file_uploader("Upload Tender Document", type=["pdf"])

    if tender_pdf is not None:
        st.write("Tender document uploaded successfully!")
        try:
            progress_text = "Processing tender document. Please wait."
            my_bar = st.progress(0, text=progress_text)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(tender_pdf.getvalue())
                tmp_file_path = tmp_file.name

            try:
                tender_pdf_markdown = PDFMarkdown(pdf_path=tmp_file_path, file_id=tender_pdf.name)
                st.write("PDF to Markdown conversion started...")
                tender_in_markdown_format = tender_pdf_markdown.pdf_to_markdown()
                st.write("PDF to Markdown conversion completed.")
                if not tender_in_markdown_format:
                    st.error("PDF to Markdown conversion failed: Empty result")
                    return
            except Exception as e:
                st.error(f"Error during PDF to Markdown conversion: {str(e)}")
                return
            finally:
                tender_pdf_markdown = None
                try:
                    os.unlink(tmp_file_path)
                except Exception as e:
                    st.warning(f"Could not delete temporary file: {str(e)}")

            my_bar.progress(100, text="Processing complete!")
            st.success("Tender document processed successfully!")
            st.write("Displaying chat container...")
            tender_qa_chat_container(llm_client, tender_in_markdown_format)

        except Exception as e:
            st.error(f"Error processing tender document: {str(e)}")
            st.write("Displaying chat container despite error...")
            tender_qa_chat_container(llm_client, "Error occurred while processing the document.")

    else:
        st.write("Please upload a tender document to start the Q&A session.")

def tender_qa_chat_container(llm_client, markdown_text):
    st.subheader("Tender Q&A Chat")
    
    st.markdown("""
        <style>
        .element-container:has(.stChatInput) {
            position: fixed;
            left: 50%;
            bottom: 20px;
            transform: translate(-50%, -50%);
            margin: 0 auto;
            z-index: 1000;
        }
        .stChatInput {
            flex-wrap: nowrap;
        }
        </style>
    """, unsafe_allow_html=True)

    prompt = st.chat_input("Ask a question about the tender document")

    if "history" not in st.session_state:
        st.session_state["history"] = []

    for message in st.session_state["history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt:
        st.session_state["history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = llm_client.call_llm(
            system_prompt=f"You are a helpful assistant. Use the following tender document to answer questions:\n\n{markdown_text}",
            user_prompt=prompt
        )

        st.session_state["history"].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

def compliance_check_tab():
    st.subheader("Compliance Check")
    st.write("This tab will contain the compliance check functionality.")

def main():
    env_vars = load_env_vars()

    if not all(env_vars.values()):
        st.error("Missing environment variables. Please check your .env file.")
        st.stop()

    st.title("Tender-POC Demo")

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    tab1, tab2, tab3 = st.tabs(["SOTR Processing", "Tender Q&A", "Compliance Check"])

    llm_client = get_llm_client(env_vars)

    with tab1:
        sotr_processing_tab(llm_client)
    with tab2:
        tender_qa_tab(llm_client)
    with tab3:
        compliance_check_tab()

if __name__ == "__main__":
    main()