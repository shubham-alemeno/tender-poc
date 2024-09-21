import streamlit as st
import logging
from utils.llm_client import LLMClient
from utils.sotr_construction import SOTRMarkdown
from utils.markdown_utils_experimental import PDFMarkdown
from utils.compliance_check import ComplianceChecker
import os
import tempfile
import io
import pandas as pd
import gc
from dotenv import load_dotenv
import traceback
from datetime import datetime

load_dotenv()


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

def sotr_document_tab(llm_client) -> None:
    
    st.write("<div style='text-align: center; font-size: 24px; margin-top: 100px;'>Complete the process to finalize Compliance Matrix</div>", unsafe_allow_html=True)
    
    if 'sotr_processed' not in st.session_state:
        st.session_state.sotr_processed = False
        st.session_state.processed_df = None
        st.session_state.last_uploaded_file = None
        st.session_state.edit_mode = False
        st.session_state.done_editing = False

    with st.sidebar:
        sotr_file_list = os.listdir('sotr_data')
        selected_file = st.selectbox('Select existing SOTR file', [''] + sotr_file_list)
        
        if selected_file and selected_file != st.session_state.last_uploaded_file:
            file_path = os.path.join('sotr_data', selected_file)
            try:
                st.session_state.processed_df = pd.read_excel(file_path)
                st.session_state.sotr_processed = True
                st.session_state.last_uploaded_file = selected_file
                st.session_state.edit_mode = False
                st.session_state.done_editing = False
            except Exception as e:
                st.error(f"Error reading selected file: {str(e)}")
        
        st.write("OR")
        
        sotr_file = st.file_uploader("Upload new SOTR Document", type=["pdf", "xlsx"])

        if sotr_file is not None and sotr_file != st.session_state.last_uploaded_file:
            st.session_state.sotr_processed = False
            st.session_state.last_uploaded_file = sotr_file
            st.session_state.edit_mode = False
            st.session_state.done_editing = False
        
        st.subheader("Final Compliance Matrix")
        final_compliance_matrix = st.file_uploader("Upload Final Compliance Matrix", type=["xlsx"])
        
        if final_compliance_matrix is not None:
            st.session_state.final_compliance_matrix = pd.read_excel(final_compliance_matrix)
            st.success("Final Compliance Matrix uploaded successfully")

        if sotr_file is not None and not st.session_state.sotr_processed:
            try:
                progress_text = "Processing SOTR document. Please wait."
                my_bar = st.progress(0, text=progress_text)

                file_content = sotr_file.read()
                file_id = f"sotr_{sotr_file.name}"

                if sotr_file.type == "application/pdf":
                    sotr = SOTRMarkdown(llm_client=llm_client)
                    
                    time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
                    estimated_pages = len(file_content) // 10000
                    ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages               
                    
                    with st.spinner(f"This might take upto {ETA_time_in_minutes:.2f} minutes"):        
                        my_bar.progress(15, text=progress_text)
                        sotr.load_from_pdf(file_content, file_id)
                        my_bar.progress(50, text=progress_text)
                        
                        try:
                            df, split_text = sotr.get_matrix_points()
                            if df.empty:
                                st.warning("No data was extracted from the document. Please check the content and try again.")
                            else:
                                my_bar.progress(75, text=progress_text)
                                st.session_state.processed_df = df
                                st.session_state.sotr_processed = True
                                my_bar.progress(100, text="Processing complete!")
                        except Exception as e:
                            st.error(f"Error in get_matrix_points: {str(e)}")
                            st.write(f"Exception type: {type(e).__name__}")
                            st.write(f"Exception details: {e.__dict__}")
                            st.write(f"Traceback: {traceback.format_exc()}")
                            st.warning("Processing completed with errors. Some sections may have been skipped.")
                
                elif sotr_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    st.session_state.processed_df = pd.read_excel(sotr_file)
                    st.session_state.sotr_processed = True
                    my_bar.progress(100, text="Processing complete!")
                
            except Exception as e:
                st.error(f"Error processing SOTR document: {str(e)}")
                st.write(f"Exception type: {type(e).__name__}")
                st.write(f"Exception details: {e.__dict__}")
                st.write(f"Traceback: {traceback.format_exc()}")
    
    if not st.session_state.sotr_processed:
        st.write("<div style='text-align: center; font-size: 24px; margin-top: 20px;'>① Select or Upload SOTR</div>", unsafe_allow_html=True)
        st.write("<div style='text-align: center; font-size: 24px; margin-top: 20px;'>② Open & Edit Compliance Matrix</div>", unsafe_allow_html=True)
        st.write("<div style='text-align: center; font-size: 24px; margin-top: 20px;'>③ Finalize Compliance Matrix</div>", unsafe_allow_html=True)
    
    elif st.session_state.sotr_processed:
        st.write("<div style='text-align: center; font-size: 24px; margin-top: 20px; margin-bottom: 40px;'>❶ Select or Upload SOTR ✔</div>", unsafe_allow_html=True)
        
        if not st.session_state.done_editing:
            left, middle, right = st.columns([1, 2, 1])
            
            with middle:
                st.write("<div style='text-align: center; font-size: 24px; margin-bottom: 20px;'>② Open & Edit Compliance Matrix</div>", unsafe_allow_html=True)
            
            with right:
                st.write("<div style='text-align: right; margin-top: 5px;'>", unsafe_allow_html=True)
                if st.button("Edit Compliance Matrix", key="edit_matrix_button"):
                    st.session_state.edit_mode = not st.session_state.edit_mode
                st.write("</div>", unsafe_allow_html=True)

            st.write("<div style='text-align: center; font-size: 24px; margin-top: 60px;'>③ Finalize Compliance Matrix</div>", unsafe_allow_html=True)

            if st.session_state.edit_mode:
                st.markdown("<div style='display: flex; justify-content: center; margin-top: 40px;'>", unsafe_allow_html=True)
                edited_df = st.data_editor(st.session_state.processed_df, hide_index=True, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='display: flex; justify-content: center; margin-top: 20px;'>", unsafe_allow_html=True)
                if st.button("Save", use_container_width=True):
                    st.session_state.processed_df = edited_df
                    st.session_state.edit_mode = False
                    st.session_state.done_editing = True
                st.markdown("</div>", unsafe_allow_html=True)
                
        
        else:
            st.write("<div style='text-align: center; font-size: 24px; margin-top: 40px;'>❷ Open & Edit Compliance Matrix ✔</div>", unsafe_allow_html=True)
            st.write("<div style='text-align: center; font-size: 24px; margin-top: 40px;'>❸ Finalize Compliance Matrix ✔</div>", unsafe_allow_html=True)

            # Automatically save the result
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_filename = f"sotr_matrix_{current_time}.xlsx"
            save_path = os.path.join('sotr_data', save_filename)
            
            try:
                st.session_state.processed_df.to_excel(save_path, index=False)
            except Exception as e:
                st.error(f"Error saving SOTR Matrix: {str(e)}")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.processed_df.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_data = output.getvalue()
        
        with st.sidebar:
            st.download_button(
                label="📥 Download SOTR Matrix",
                data=excel_data,
                file_name="sotr_matrix.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

@st.fragment
def sotr_chat_container(llm_client):
    st.markdown("""
        <style>
        .element-container:has(.stChatInput) {
            position: fixed;
            left: 60%;
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
    prompt = st.chat_input("Ask anything about the SOTR document")

    if "sotr_history" not in st.session_state:
        st.session_state["sotr_history"] = []

    for message in st.session_state["sotr_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt:
        st.session_state["sotr_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Answering..."):
            response = llm_client.call_llm(
                system_prompt=f"You are a helpful assistant.",
                user_prompt=prompt
            )

            st.session_state["sotr_history"].append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

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

def tender_qa_tab(llm_client) -> None:
    with st.sidebar:
        st.subheader("Tender Q&A")
        tender_files = [f for f in os.listdir('tender_data') if os.path.isfile(os.path.join('tender_data', f))]
        selected_tenders = st.multiselect("Select Processed Tender", options=tender_files, key="selected_tenders")
        uploaded_file = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_qa_pdf_uploader")
        st.session_state["pdf_processed"] = False
        tender_in_markdown_format = None
    
    if selected_tenders:
        tender_in_markdown_format = ""
        for tender_file in selected_tenders:
            with open(os.path.join('tender_data', tender_file), 'r') as f:
                tender_in_markdown_format += f.read() + "\n\n"
        st.session_state["pdf_processed"] = True
    
    elif uploaded_file is not None:
        st.session_state["tender_document"] = uploaded_file
        st.session_state["pdf_processed"] = False
        st.success("Tender Document uploaded successfully")
        try:
            file_content = uploaded_file.getvalue()
            time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
            estimated_pages = len(file_content) // 10000
            ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages
            
            progress_text = "Started processing tender document : 0% complete"
            my_bar = st.progress(0, text=progress_text)

            with st.spinner(f"This might take upto {ETA_time_in_minutes:.2f} minutes"):
                def update_progress(step, step_name):
                    print(f"Step {step_name}: {step}")
                    progress = int(step)
                    my_bar.progress(progress, text=f"{step_name} : {int(step)}% complete")

                tender_in_markdown_format = convert_pdf_to_markdown(file_content, uploaded_file.name, update_progress)

            if not tender_in_markdown_format:
                st.error("PDF to Markdown conversion failed: Empty result")
                return

            my_bar.progress(100, text="Processing complete!")
            st.session_state["pdf_processed"] = True
           
        except Exception as e:
            st.error(f"Error processing tender document: {str(e)}")
    else:
        pass

    if st.session_state["pdf_processed"] and tender_in_markdown_format is not None:
        tender_qa_chat_container(llm_client, tender_in_markdown_format)


@st.fragment
def tender_qa_chat_container(llm_client, markdown_text) -> None:
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

        with st.spinner("Answering..."):
            response = llm_client.call_llm(
                system_prompt=f"You are a helpful assistant. Use the following tender document to answer questions:\n\n{markdown_text}",
                user_prompt=prompt
            )

            st.session_state["history"].append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

def compliance_matrix_tab() -> None:
    st.write("<div style='text-align: center; font-size: 24px; margin-top: 20px;'>Compliance Check</div>", unsafe_allow_html=True)

    compliance_checker = ComplianceChecker()

    col1, col2 = st.columns(2)

    with col1:
        if 'final_compliance_matrix' not in st.session_state:
            final_compliance_matrix = st.file_uploader("Upload Final Compliance Matrix", type=["xlsx"], key="final_compliance_matrix_uploader")
            if final_compliance_matrix is not None:
                compliance_checker.load_matrix(final_compliance_matrix.read())
                st.session_state['final_compliance_matrix'] = final_compliance_matrix
                st.success("Final Compliance Matrix uploaded successfully.")
        else:
            st.success("Final Compliance Matrix is already uploaded.")

    with col2:
        if 'tender_document' not in st.session_state:
            tender_document = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_document_uploader")
            if tender_document is not None:
                compliance_checker.load_tender(tender_document.read())
                st.session_state['tender_document'] = tender_document
                st.success("Tender Document uploaded successfully.")
        else:
            st.success("Tender Document is already uploaded.")

    if 'final_compliance_matrix' in st.session_state and 'tender_document' in st.session_state:
        if st.button("Run Compliance Check"):
            with st.spinner("Running compliance check..."):
                results = compliance_checker.check_compliance()
                st.session_state['compliance_results'] = results
            st.success("Compliance check completed.")

    if 'compliance_results' in st.session_state:
        st.write("Compliance Check Results:")
        st.dataframe(st.session_state['compliance_results'])

        with st.sidebar:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state['compliance_results'].to_excel(writer, index=False, sheet_name='Compliance Results')
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Download Compliance Results",
                data=excel_data,
                file_name="compliance_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def color_rows(row):
    color_map = {
        'Yes': 'background-color: #006400',  # Dark green
        'Partial': 'background-color: #8B8000',  # Dark yellow
        'No': 'background-color: #8B0000'  # Dark red
    }
    return [color_map.get(row['Status'], '') for _ in row]
        

def main():
    st.set_page_config(page_title="Alemeno",layout="wide")
    st.sidebar.title('Alemeno')

    st.markdown("""<style>div.stButton > button:first-child {    background-color: #252525;    border: 1px solid #353535;}</style>""", unsafe_allow_html=True)

    env_vars = load_env_vars()

    if not all(env_vars.values()):
        st.error("Missing environment variables. Please check your .env file.")
        st.stop()

    st.title("Tender-POC Demo")

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    tab1, tab2, tab3 = st.tabs(["SOTR Document", "Tender Q&A", "Compliance Matrix"])

    llm_client = get_llm_client(env_vars)

    with tab1:
        sotr_document_tab(llm_client)
    with tab2:
        tender_qa_tab(llm_client)
    with tab3:
        compliance_matrix_tab()

if __name__ == "__main__":
    main()