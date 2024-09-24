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

    # with st.sidebar:
    #     sotr_file_list = os.listdir('sotr_data')
    #     selected_file = st.selectbox('Select existing SOTR file', [''] + sotr_file_list)
        
    #     if selected_file and selected_file != st.session_state.last_uploaded_file:
    #         file_path = os.path.join('sotr_data', selected_file)
    #         try:
    #             st.session_state.processed_df = pd.read_excel(file_path)
    #             st.session_state.sotr_processed = True
    #             st.session_state.last_uploaded_file = selected_file
    #             st.session_state.edit_mode = False
    #             st.session_state.done_editing = False
    #         except Exception as e:
    #             st.error(f"Error reading selected file: {str(e)}")
        
    #     st.write("OR")
        
    #     sotr_file = st.file_uploader("Upload new SOTR Document", type=["pdf", "xlsx"])

    #     if sotr_file is not None and sotr_file != st.session_state.last_uploaded_file:
    #         st.session_state.sotr_processed = False
    #         st.session_state.last_uploaded_file = sotr_file
    #         st.session_state.edit_mode = False
    #         st.session_state.done_editing = False
        
    #     st.subheader("Final Compliance Matrix")
    #     final_compliance_matrix = st.file_uploader("Upload Final Compliance Matrix", type=["xlsx"])
        
    #     if final_compliance_matrix is not None:
    #         st.session_state.final_compliance_matrix = pd.read_excel(final_compliance_matrix)
    #         st.success("Final Compliance Matrix uploaded successfully")

    #     if sotr_file is not None and not st.session_state.sotr_processed:
    #         try:
    #             progress_text = "Processing SOTR document. Please wait."
    #             my_bar = st.progress(0, text=progress_text)

    #             file_content = sotr_file.read()
    #             file_id = f"sotr_{sotr_file.name}"

    #             if sotr_file.type == "application/pdf":
    #                 sotr = SOTRMarkdown(llm_client=llm_client)
                    
    #                 time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
    #                 estimated_pages = len(file_content) // 10000
    #                 ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages               
                    
    #                 with st.spinner(f"This might take upto {ETA_time_in_minutes:.2f} minutes"):        
    #                     my_bar.progress(15, text=progress_text)
    #                     sotr.load_from_pdf(file_content, file_id)
    #                     my_bar.progress(50, text=progress_text)
                        
    #                     try:
    #                         df, split_text = sotr.get_matrix_points()
    #                         if df.empty:
    #                             st.warning("No data was extracted from the document. Please check the content and try again.")
    #                         else:
    #                             my_bar.progress(75, text=progress_text)
    #                             st.session_state.processed_df = df
    #                             st.session_state.sotr_processed = True
    #                             my_bar.progress(100, text="Processing complete!")
    #                     except Exception as e:
    #                         st.error(f"Error in get_matrix_points: {str(e)}")
    #                         st.write(f"Exception type: {type(e).__name__}")
    #                         st.write(f"Exception details: {e.__dict__}")
    #                         st.write(f"Traceback: {traceback.format_exc()}")
    #                         st.warning("Processing completed with errors. Some sections may have been skipped.")
                
    #             elif sotr_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
    #                 st.session_state.processed_df = pd.read_excel(sotr_file)
    #                 st.session_state.sotr_processed = True
    #                 my_bar.progress(100, text="Processing complete!")
                
    #         except Exception as e:
    #             st.error(f"Error processing SOTR document: {str(e)}")
    #             st.write(f"Exception type: {type(e).__name__}")
    #             st.write(f"Exception details: {e.__dict__}")
    #             st.write(f"Traceback: {traceback.format_exc()}")
    
    if not st.session_state.sotr_processed:
        st.markdown(
                """
                <style>
                    .stButton {
                        display: flex;
                        justify-content: center;
                    }
                </style>
                """,
                unsafe_allow_html=True
            )
        if st.button("① Select or Upload SOTR"):
            @st.dialog("Select or Upload SOTR")
            def sotr_dialog():
                st.write("Choose an option to load SOTR document:")
                sotr_file = st.file_uploader("Upload new SOTR Document", type=["pdf", "xlsx"], key="sotr_file_upload")
                if sotr_file:
                    try:
                        progress_text = "Processing SOTR document. Please wait."
                        my_bar = st.progress(0, text=progress_text)

                        if sotr_file.type == "application/pdf":
                            sotr = SOTRMarkdown(llm_client=llm_client)
                            file_content = sotr_file.read()
                            file_id = f"sotr_{sotr_file.name}"

                            time_taken_to_convert_PDF_to_markdown_per_page_in_minutes = 0.5
                            estimated_pages = len(file_content) // 10000
                            ETA_time_in_minutes = time_taken_to_convert_PDF_to_markdown_per_page_in_minutes * estimated_pages               
                            
                            with st.spinner(f"This might take upto {ETA_time_in_minutes:.2f} minutes"):        
                                my_bar.progress(15, text=progress_text)
                                sotr.load_from_pdf(file_content, file_id)
                                my_bar.progress(50, text=progress_text)
                                
                                df, _ = sotr.get_matrix_points()
                                if df.empty:
                                    st.warning("No data was extracted from the document. Please check the content and try again.")
                                else:
                                    my_bar.progress(75, text=progress_text)
                                    st.session_state.processed_df = df
                                    my_bar.progress(100, text="Processing complete!")
                        elif sotr_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                            st.session_state.processed_df = pd.read_excel(sotr_file)
                            my_bar.progress(100, text="Processing complete!")
                        
                        st.session_state.sotr_processed = True
                        st.session_state.last_uploaded_file = sotr_file
                        st.session_state.edit_mode = False
                        st.session_state.done_editing = False
                        st.success("File uploaded and processed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")

            sotr_dialog()

        st.button("② Open & Edit Compliance Matrix", disabled=True)
        
        if st.button("③ Finalize Compliance Matrix"):
            @st.dialog("Finalize Compliance Matrix")
            def finalize_dialog():
                st.write("Upload the Final Compliance Matrix")
                final_compliance_matrix = st.file_uploader("Upload Final Compliance Matrix", type=["xlsx"], key="final_compliance_matrix_upload")
                if final_compliance_matrix is not None:
                    try:
                        st.session_state.final_compliance_matrix = pd.read_excel(final_compliance_matrix)
                        if st.session_state.final_compliance_matrix is not None:
                            st.session_state.processed_df = st.session_state.final_compliance_matrix
                        st.session_state.sotr_processed = True
                        st.session_state.done_editing = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error reading Final Compliance Matrix: {str(e)}")
            finalize_dialog()

    
    elif st.session_state.sotr_processed:
        st.markdown(
                """
                <style>
                    .stButton {
                        display: flex;
                        justify-content: center;
                    }
                </style>
                """,
                unsafe_allow_html=True
            )
        st.button("❶ Select or Upload SOTR ✔", disabled=True)
        
        if not st.session_state.done_editing:
            st.markdown(
                """
                <style>
                    .stButton {
                        display: flex;
                        justify-content: center;
                    }
                    .stDownloadButton {
                        display: flex;
                        justify-content: center;
                    }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.processed_df.to_excel(writer, index=False, sheet_name='Sheet1')
            excel_data = output.getvalue()
            if not st.session_state.get('step_2_complete'):
                if st.download_button("② Open Compliance Matrix", excel_data, file_name="compliance_matrix.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                    st.session_state.step_2_complete = True
                    st.rerun()
            else:
                st.button("❷ Open & Edit Compliance Matrix ✔", disabled=True)
            

            if st.button("③ Finalize Compliance Matrix"):
                @st.dialog("Finalize Compliance Matrix")
                def finalize_dialog():
                    st.write("Upload the Final Compliance Matrix")
                    final_compliance_matrix = st.file_uploader("Upload Final Compliance Matrix", type=["xlsx"], key="final_compliance_matrix_upload")
                    if final_compliance_matrix is not None:
                        try:
                            st.session_state.final_compliance_matrix = pd.read_excel(final_compliance_matrix)
                            if st.session_state.final_compliance_matrix is not None:
                                st.session_state.processed_df = st.session_state.final_compliance_matrix
                            st.session_state.sotr_processed = True
                            st.session_state.done_editing = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error reading Final Compliance Matrix: {str(e)}")
                finalize_dialog()

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
            st.button("❷ Open & Edit Compliance Matrix ✔", disabled=True)
            st.button("❸ Finalize Compliance Matrix ✔", disabled=True)

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
        
        # with st.sidebar:
        #     st.download_button(
        #         label="📥 Download SOTR Matrix",
        #         data=excel_data,
        #         file_name="sotr_matrix.xlsx",
        #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        #     )

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
    # tender_files = [f for f in os.listdir('tender_data') if os.path.isfile(os.path.join('tender_data', f))]
    uploaded_file = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_qa_pdf_uploader")
    # st.markdown("<div style='text-align: center; margin: 10px 0;'>OR</div>", unsafe_allow_html=True)
    # selected_tenders = st.multiselect("Select Processed Tender", options=tender_files, key="selected_tenders")
    st.session_state["pdf_processed"] = False
    tender_in_markdown_format = None
    
    # if selected_tenders:
    #     tender_in_markdown_format = ""
    #     for tender_file in selected_tenders:
    #         with open(os.path.join('tender_data', tender_file), 'r') as f:
    #             tender_in_markdown_format += f.read() + "\n\n"
    #     st.session_state["pdf_processed"] = True
    
    if uploaded_file is not None:
        st.session_state["tender_document"] = uploaded_file
        st.session_state["pdf_processed"] = False
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
            try:
                st.info(f"Debug: Tender document in session state: {st.session_state['tender_document'] is not None}")
                st.info(f"Debug: Final compliance matrix in session state: {st.session_state['final_compliance_matrix'] is not None}")
                
                if compliance_checker.tender_markdown is None:
                    st.error("Tender document not loaded. Attempting to reload...")
                    if 'tender_document' in st.session_state:
                        compliance_checker.load_tender(st.session_state['tender_document'].read())
                    
                    if compliance_checker.tender_markdown is None:
                        st.error("Failed to reload tender document. Please upload the tender document again.")
                    else:
                        st.success("Tender document reloaded successfully.")
                
                if compliance_checker.sotr_matrix_content is None:
                    st.error("SOTR matrix not loaded. Attempting to reload...")
                    if 'final_compliance_matrix' in st.session_state:
                        compliance_checker.load_matrix(st.session_state['final_compliance_matrix'].read())
                    
                    if compliance_checker.sotr_matrix_content is None:
                        st.error("Failed to reload SOTR matrix. Please upload the compliance matrix again.")
                    else:
                        st.success("SOTR matrix reloaded successfully.")
                
                if compliance_checker.tender_markdown is not None and compliance_checker.sotr_matrix_content is not None:
                    with st.spinner("Running compliance check..."):
                        results = compliance_checker.check_compliance()
                        st.session_state['compliance_results'] = results
                    st.success("Compliance check completed.")
                else:
                    st.error("Cannot run compliance check. Please ensure both documents are properly loaded.")
            except Exception as e:
                st.error(f"Error during compliance check: {str(e)}")
                st.info("Please ensure both the Final Compliance Matrix and Tender Document are properly loaded.")
                st.info(f"Debug info - Tender markdown: {compliance_checker.tender_markdown is not None}, SOTR matrix: {compliance_checker.sotr_matrix_content is not None}")
                st.info(f"Tender markdown length: {len(compliance_checker.tender_markdown) if compliance_checker.tender_markdown else 'N/A'}")
                st.info(f"SOTR matrix shape: {compliance_checker.sotr_matrix_content.shape if compliance_checker.sotr_matrix_content is not None else 'N/A'}")
                if compliance_checker.tender_markdown:
                    st.info(f"First 100 characters of tender markdown: {compliance_checker.tender_markdown[:100]}...")
                if compliance_checker.sotr_matrix_content is not None:
                    st.info(f"First few rows of SOTR matrix: {compliance_checker.sotr_matrix_content.head().to_string()}")
                    st.info(f"SOTR matrix columns: {compliance_checker.sotr_matrix_content.columns.tolist()}")
                    st.info(f"SOTR matrix data types: {compliance_checker.sotr_matrix_content.dtypes}")
                    
                    # Check if 'Clause' column exists
                    if 'Clause' in compliance_checker.sotr_matrix_content.columns:
                        st.info(f"Sample of 'Clause' column: {compliance_checker.sotr_matrix_content['Clause'].head().tolist()}")
                    else:
                        st.warning("'Clause' column not found in SOTR matrix")

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