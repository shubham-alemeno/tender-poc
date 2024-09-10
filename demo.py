import streamlit as st
import logging
from utils.llm_client import LLMClient
from utils.sotr_construction import SOTRMarkdown
from utils.markdown_utils import PDFMarkdown
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
    st.subheader("SOTR Processing")
    st.write("This tab will contain the SOTR processing functionality.")

    file_type = st.radio("Choose file type to upload:", ("PDF", "Processed Markdown"))
    
    if file_type == "PDF":
        sotr_file = st.file_uploader("Upload SOTR Document", type=["pdf"])
    else:
        sotr_file = st.file_uploader("Upload Processed Markdown", type=["md"])

    if sotr_file is not None:
        st.write(f"{file_type} uploaded successfully!")

        try:
            progress_text = "Processing SOTR document. Please wait."
            my_bar = st.progress(0, text=progress_text)

            file_content = sotr_file.read()
            file_id = f"sotr_{sotr_file.name}"
            sotr = SOTRMarkdown(llm_client=llm_client)
            
            my_bar.progress(25, text=progress_text)
            
            if file_type == "PDF":
                sotr.load_from_pdf(file_content, file_id)
                markdown_text = sotr.markdown_text
                
                st.download_button(
                    label="📥 Download Processed Markdown",
                    data=markdown_text,
                    file_name="processed_sotr.md",
                    mime="text/markdown"
                )
            else:
                markdown_text = file_content.decode("utf-8")
                sotr.load_from_md(markdown_text, file_id)
            
            my_bar.progress(50, text=progress_text)
            
            st.write("Before get_matrix_points")
            try:
                markdown_text_splits = sotr.split_markdown_by_headers()
                st.write(f"Number of markdown splits: {len(markdown_text_splits)}")
                
                cleaned_text_splits = []
                for point in markdown_text_splits:
                    if 'metadata' in point and 'Header 2' in point.metadata:
                        section_header = point.metadata["Header 2"]
                        section_no = section_header.split(" ")[0]
                        if point.page_content.strip():
                            cleaned_text_splits.append({"section": section_no, "content": point.page_content})
                
                st.write(f"Number of cleaned text splits: {len(cleaned_text_splits)}")
                
                df, split_text = sotr.get_matrix_points()
                if df.empty:
                    st.warning("No data was extracted from the document. Please check the content and try again.")
                else:
                    my_bar.progress(75, text=progress_text)
                    
                    st.write(f"DataFrame shape: {df.shape}")

                    st.data_editor(df, width=4000, hide_index=True)
                    
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
                st.error(f"Error in get_matrix_points: {str(e)}")
                st.write(f"Exception type: {type(e).__name__}")
                st.write(f"Exception details: {e.__dict__}")
                st.write(f"Traceback: {traceback.format_exc()}")
                st.warning("Processing completed with errors. Some sections may have been skipped.")
            st.write("After get_matrix_points")
            
        except Exception as e:
            st.error(f"Error processing SOTR document: {str(e)}")
            st.write(f"Exception type: {type(e).__name__}")
            st.write(f"Exception details: {e.__dict__}")
            st.write(f"Traceback: {traceback.format_exc()}")

@st.cache_data
def convert_pdf_to_markdown(file_content, file_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name

    try:
        tender_pdf_markdown = PDFMarkdown(pdf_path=tmp_file_path, file_id=file_name)
        tender_in_markdown_format = tender_pdf_markdown.pdf_to_markdown(file_content)
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
    st.subheader("Tender Q&A")
    
    file_type = st.radio("Choose file type to upload:", ("PDF", "Processed Markdown"), key="tender_qa_file_type")
    
    if file_type == "PDF":
        uploaded_file = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_qa_pdf_uploader")
    else:
        uploaded_file = st.file_uploader("Upload Processed Markdown", type=["md"], key="tender_qa_md_uploader")

    if uploaded_file is not None:
        st.write(f"{file_type} uploaded successfully!")
        
        if file_type == "PDF":
            try:
                progress_text = "Processing tender document. Please wait."
                my_bar = st.progress(0, text=progress_text)

                tender_in_markdown_format = convert_pdf_to_markdown(uploaded_file.getvalue(), uploaded_file.name)
                
                if not tender_in_markdown_format:
                    st.error("PDF to Markdown conversion failed: Empty result")
                    return
                
                st.download_button(
                    label="📥 Download Processed Markdown",
                    data=tender_in_markdown_format,
                    file_name="processed_tender.md",
                    mime="text/markdown"
                )

                my_bar.progress(100, text="Processing complete!")
                st.success("Tender document processed successfully!")
            except Exception as e:
                st.error(f"Error processing tender document: {str(e)}")
                tender_in_markdown_format = "Error occurred while processing the document."
        else:
            tender_in_markdown_format = uploaded_file.getvalue().decode("utf-8")
        
        st.write("Displaying chat container...")
        tender_qa_chat_container(llm_client, tender_in_markdown_format)
    else:
        st.write("Please upload a document to start the Q&A session.")

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