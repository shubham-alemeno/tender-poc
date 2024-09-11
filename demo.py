import streamlit as st
import logging
from utils.llm_client import LLMClient
from utils.sotr_construction import SOTRMarkdown
from utils.markdown_utils_experimental import PDFMarkdown
import os
import tempfile
import io
import pandas as pd
import gc
from dotenv import load_dotenv
load_dotenv()
import traceback

@st.cache_data
def load_env_vars():
    required_vars = ["ANTHROPIC_MODEL", "ANTHROPIC_API_KEY"]
    env_vars = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
        else:
            env_vars[var.lower()] = value

    if missing_vars:
        st.error(f"Missing environment variables: {', '.join(missing_vars)}")
        st.info("Please set these variables in your .env file or environment.")
        return None

    return env_vars

@st.cache_resource
def get_llm_client(env_vars):
    return LLMClient(anthropic_model=env_vars.get('anthropic_model'))

def sotr_processing_tab(llm_client):
    sotr_file = st.file_uploader("Upload SOTR Document", type=["pdf"])

    if sotr_file is not None:
        try:
            progress_text = "Processing SOTR document. Please wait."
            my_bar = st.progress(0, text=progress_text)

            file_content = sotr_file.read()
            file_id = f"sotr_{sotr_file.name}"
            sotr = SOTRMarkdown(llm_client=llm_client)

            time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
            estimated_pages = len(file_content) // 10000
            ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages               
            st.write(f"Estimated time to complete: {ETA_time_in_minutes:.2f} minutes")
            
            my_bar.progress(15, text=progress_text)

            sotr.load_from_pdf(file_content, file_id)
            
            my_bar.progress(50, text=progress_text)
            
            try:
                df, split_text = sotr.get_matrix_points()
                if df.empty:
                    st.warning("No data was extracted from the document. Please check the content and try again.")
                else:
                    my_bar.progress(75, text=progress_text)                    
                    st.write("<div style='text-align: center;'><strong> SOTR Matrix </strong></div>", unsafe_allow_html=True)
                    
                    edited_df = st.data_editor(
                        df,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Sr. No.": st.column_config.NumberColumn(width="small"),
                            "Clause": st.column_config.TextColumn(width="large"),
                            "Clause Reference": st.column_config.TextColumn(width="small")
                        }
                    )
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        edited_df.to_excel(writer, index=False, sheet_name='Sheet1')
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
                st.error(f"Error in get_matrix_points: {str(e)}")
                st.write(f"Exception type: {type(e).__name__}")
                st.write(f"Exception details: {e.__dict__}")
                st.write(f"Traceback: {traceback.format_exc()}")
                st.warning("Processing completed with errors. Some sections may have been skipped.")
            
        except Exception as e:
            st.error(f"Error processing SOTR document: {str(e)}")
            st.write(f"Exception type: {type(e).__name__}")
            st.write(f"Exception details: {e.__dict__}")
            st.write(f"Traceback: {traceback.format_exc()}")

def convert_pdf_to_markdown(file_content, file_name, progress_callback=None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name

    try:
        tender_pdf_markdown = PDFMarkdown(pdf_path=tmp_file_path, file_id=file_name)
        
        tender_in_markdown_format = tender_pdf_markdown.pdf_to_markdown(file_content, progress_callback=progress_callback)
        return tender_in_markdown_format
    finally:
        tender_pdf_markdown = None
        gc.collect()
        import time
        time.sleep(0.1)
        try:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        except Exception as e:
            st.warning(f"Could not delete temporary file: {str(e)}")

def tender_qa_tab(llm_client):
    uploaded_file = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_qa_pdf_uploader")

    if uploaded_file is not None:
        try:
            file_content = uploaded_file.getvalue()
            time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
            estimated_pages = len(file_content) // 10000
            ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages
            st.write(f"Estimated time to complete: {ETA_time_in_minutes:.2f} minutes")
            
            progress_text = "Processing tender document. Please wait."
            my_bar = st.progress(0, text=progress_text)

            with st.spinner('Running PDF pre-processing...'):
                def update_progress(step, step_name):
                    progress = int((step  * 100))
                    my_bar.progress(progress, text=f"{progress_text} {int((step  * 100))}% complete")

                tender_in_markdown_format = convert_pdf_to_markdown(file_content, uploaded_file.name, update_progress)

            if not tender_in_markdown_format:
                st.error("PDF to Markdown conversion failed: Empty result")
                return

            my_bar.progress(100, text="Processing complete!")

            tender_qa_chat_container(llm_client, tender_in_markdown_format)
        except Exception as e:
            st.error(f"Error processing tender document: {str(e)}")
    else:
        pass

def tender_qa_chat_container(llm_client, markdown_text):
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
    st.subheader("Working In Progress...")

def main():
    st.set_page_config(layout="wide")

    env_vars = load_env_vars()

    if not all(env_vars.values()):
        st.error("Missing environment variables. Please check your .env file.")
        st.stop()

    st.title("Tender-POC Demo")

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    tab1, tab2, tab3 = st.tabs(["SOTR Processing", "Tender Q&A", "Compliance Check (WIP)"])

    llm_client = get_llm_client(env_vars)

    with tab1:
        sotr_processing_tab(llm_client)
    with tab2:
        tender_qa_tab(llm_client)
    with tab3:
        compliance_check_tab()

if __name__ == "__main__":
    main()