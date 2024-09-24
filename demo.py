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
import json

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
    uploaded_file = st.file_uploader("Upload Tender Document", type=["pdf"], key="tender_qa_pdf_uploader")
    st.session_state["pdf_processed"] = False
    tender_in_markdown_format = None
    
    if uploaded_file is not None:
        st.session_state["tender_document"] = uploaded_file
        st.session_state["pdf_processed"] = False
        
        if uploaded_file.name == "TechOffer_RefPlant_GRSE.pdf":
            try:
                with open(os.path.join('tender_data', 'TechOffer_RefPlant_GRSE.md'), 'r') as f:
                    tender_in_markdown_format = f.read()
                st.session_state["pdf_processed"] = True
                st.session_state["tender_markdown"] = tender_in_markdown_format
            except FileNotFoundError:
                pass
        
        if not st.session_state["pdf_processed"]:
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
                st.session_state["tender_markdown"] = tender_in_markdown_format
           
            except Exception as e:
                st.error(f"Error processing tender document: {str(e)}")
    else:
        pass

    if st.session_state["pdf_processed"] and "tender_markdown" in st.session_state:
        tender_qa_chat_container(llm_client, st.session_state["tender_markdown"])


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
        .json-response {
            background-color: rgba(38, 39, 48, 0.5);
            border-radius: 0.5rem;
            padding: 10px;
            margin-top: 10px;
        }
        .json-key {
            color: rgb(255, 108, 108);
            font-weight: bold;
        }
        .json-value {
            color: rgb(250, 250, 250);
        }
        .json-list {
            margin-left: 20px;
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
                system_prompt=f"""You are an AI assistant specialized in analyzing tender documents. Your task is to answer questions based on the extracted text from a tender document. Follow these instructions carefully:

1. Analyze the provided extracted text from the tender document.
2. Answer the given question based solely on the information in the extracted text.
3. Provide your response in a JSON format with the following structure:
   {{
     "answer": "Your concise answer to the question",
     "references": ["List of exact text quotes from the document used to form the answer"],
     "reasoning": "Your step-by-step reasoning for the answer based on the extracted text references"
   }}
4. Ensure that your answer is directly supported by the text in the document.
5. If the question cannot be answered based on the provided text, state this in the "answer" field and explain why in the "reasoning" field.
6. Use the "references" array to list all relevant quotes from the document that support your answer. Each quote should be an exact match to the text in the document.
7. In the "reasoning" field, explain how you arrived at your answer using the references provided.
8. Your response must be a valid JSON object and nothing else. Do not include any text outside of the JSON structure.

The following is the extracted text from the tender document:

{markdown_text}

Now, provide your answer based on the given extracted text and question, ensuring it is in the correct JSON format.""",
                user_prompt=prompt
            )

            st.session_state["history"].append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                try:
                    # Find the start of the JSON object
                    json_start = response.find('{')
                    if json_start == -1:
                        raise ValueError("No JSON object found in the response")
                    
                    # Extract the JSON part of the response
                    json_response = json.loads(response[json_start:])
                    
                    st.markdown("<div class='json-response' style='background-color: rgba(38, 39, 48, 0.5); padding: 10px; border-radius: 5px;'>", unsafe_allow_html=True)
                    st.markdown("<span class='json-key'>Answer:</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='json-value'>{json_response['answer']}</span>", unsafe_allow_html=True)
                    
                    st.markdown("<span class='json-key'>References:</span>", unsafe_allow_html=True)
                    for ref in json_response["references"]:
                        st.code(ref, language="text")
                    
                    st.markdown("<span class='json-key'>Reasoning:</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='json-value'>{json_response['reasoning']}</span>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                except (json.JSONDecodeError, ValueError) as e:
                    st.error(f"Error processing response: {str(e)}")
                    st.markdown("Raw response:")
                    st.markdown(response)

def compliance_matrix_tab():
    st.write("<div style='text-align: center; font-size: 24px; margin-top: 100px;'>Compliance Check</div>", unsafe_allow_html=True)

    sotr_matrix = None
    tender_document = None

    if 'processed_df' in st.session_state and st.session_state.processed_df is not None and not st.session_state.processed_df.empty:
        sotr_matrix = st.session_state.processed_df
        st.success("SOTR matrix loaded from session state")
    else:
        sotr_file = st.file_uploader("Upload SOTR Matrix", type=["xlsx"])
        if sotr_file is not None:
            sotr_matrix = pd.read_excel(sotr_file)
            st.success("SOTR matrix uploaded successfully")

    if 'tender_markdown' in st.session_state and st.session_state.tender_markdown:
        tender_document = st.session_state.tender_markdown
        st.success("Tender document loaded from session state")
    else:
        tender_file = st.file_uploader("Upload Tender Document", type=["pdf"])
        if tender_file is not None:
            tender_document = convert_pdf_to_markdown(tender_file.getvalue(), tender_file.name)
            st.success("Tender document uploaded and converted to markdown successfully")

    if sotr_matrix is not None and tender_document is not None:
        if st.button("Run Compliance Check"):
            with st.spinner("Running compliance check..."):
                compliance_checker = ComplianceChecker()
                if isinstance(sotr_matrix, pd.DataFrame):
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        sotr_matrix.to_excel(writer, index=False)
                    compliance_checker.load_matrix(buffer.getvalue())
                elif isinstance(sotr_matrix, bytes):
                    compliance_checker.load_matrix(sotr_matrix)
                else:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        pd.read_excel(sotr_matrix).to_excel(writer, index=False)
                    compliance_checker.load_matrix(buffer.getvalue())
                
                if isinstance(tender_document, str):
                    compliance_checker.load_tender(tender_document.encode('utf-8'))
                elif isinstance(tender_document, bytes):
                    compliance_checker.load_tender(tender_document)
                else:
                    raise ValueError("Unsupported tender document type")
                
                compliance_results = compliance_checker.check_compliance()

                st.write("Compliance Check Results:")
                st.dataframe(compliance_results.style.apply(color_rows, axis=1))

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