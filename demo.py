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
from datetime import datetime
import json
import re
import requests

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

                        if sotr_file.name == "SOTR-Cleaned-V4.pdf":
                            try:
                                xlsx_path = os.path.join('sotr_data', 'SOTR-Cleaned-V4.xlsx')
                                st.session_state.processed_df = pd.read_excel(xlsx_path)
                                my_bar.progress(100, text="Processing complete!")
                            except FileNotFoundError:
                                st.error("Corresponding Excel file not found. Processing as a new PDF.")
                                process_pdf()
                        elif sotr_file.type == "application/pdf":
                            process_pdf()
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

                def process_pdf():
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
            color: #ff6c6c;
            font-weight: bold;
            font-style: italic;
        }
        .json-value {
            color: #fafafa;
        }
        .json-list {
            margin-left: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                else:
                    if isinstance(message["content"], dict):
                        if "error" in message["content"]:
                            st.error(f"Error: {message['content']['error']}")
                            st.markdown("Raw response:")
                            st.markdown(message['content']['raw_response'])
                        else:
                            st.markdown('<p class="json-key">Answer:</p>', unsafe_allow_html=True)
                            st.write(message['content']['answer'])
                            
                            st.markdown('<p class="json-key">References:</p>', unsafe_allow_html=True)
                            for ref in message['content']["references"]:
                                st.code(ref, language="text")
                            
                            st.markdown('<p class="json-key">Reasoning:</p>', unsafe_allow_html=True)
                            st.write(message['content']['reasoning'])

    spinner_placeholder = st.empty()

    prompt = st.chat_input("Ask a question about the tender document")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with spinner_placeholder.container():
            with st.spinner("Answering..."):
                try:
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
    9. Ensure that all string values in the JSON response are properly escaped, especially for newlines and control characters.

    The following is the extracted text from the tender document:

    {markdown_text}

    Now, provide your answer based on the given extracted text and question, ensuring it is in the correct JSON format.""",
                        user_prompt=prompt
                    )

                    if response is None:
                        st.warning("Rate limit reached. Please try again after some time.")
                        return

                    json_start = response.find('{')
                    if json_start == -1:
                        raise ValueError("No JSON object found in the response")
                    
                    json_end = response.rfind('}')
                    if json_end == -1:
                        raise ValueError("No closing brace found in the response")
                    
                    json_string = response[json_start:json_end+1]
                    json_string = re.sub(r'[\x00-\x1F\x7F-\x9F]|(?<!\\)\\(?!["\\\/bfnrt])|[\ud800-\udfff]|"\s*(?:(?![\x20-\x7E]).)*\s*"', 
                                         lambda m: '' if re.match(r'[\x00-\x1F\x7F-\x9F]', m.group()) else 
                                                   '\\n' if m.group() == '\n' else 
                                                   '\\r' if m.group() == '\r' else 
                                                   '\\t' if m.group() == '\t' else 
                                                   '\\b' if m.group() == '\b' else 
                                                   '\\f' if m.group() == '\f' else 
                                                   m.group().encode('unicode_escape').decode() if re.match(r'[\ud800-\udfff]', m.group()) else 
                                                   '', 
                                         json_string)
                    
                    # Handle potential JSON parsing errors
                    try:
                        json_response = json.loads(json_string)
                    except json.JSONDecodeError:
                        # Attempt to fix common JSON issues
                        json_string = json_string.replace("'", '"')  # Replace single quotes with double quotes
                        json_string = re.sub(r',\s*}', '}', json_string)  # Remove trailing commas
                        json_string = re.sub(r',\s*]', ']', json_string)
                        try:
                            json_response = json.loads(json_string)
                        except json.JSONDecodeError:
                            raise ValueError("Unable to parse JSON response after attempted fixes")
                    
                    # Validate JSON structure
                    required_keys = ["answer", "references", "reasoning"]
                    if not all(key in json_response for key in required_keys):
                        missing_keys = [key for key in required_keys if key not in json_response]
                        raise ValueError(f"JSON response is missing required keys: {', '.join(missing_keys)}")
                    
                    st.session_state.messages.append({"role": "assistant", "content": json_response})
                    
                    with chat_container:
                        with st.chat_message("assistant"):
                            st.markdown('<p class="json-key">Answer:</p>', unsafe_allow_html=True)
                            st.write(json_response['answer'])
                            
                            st.markdown('<p class="json-key">References:</p>', unsafe_allow_html=True)
                            for ref in json_response["references"]:
                                st.code(ref, language="text")
                            
                            st.markdown('<p class="json-key">Reasoning:</p>', unsafe_allow_html=True)
                            st.write(json_response['reasoning'])
                    
                except (json.JSONDecodeError, ValueError) as e:
                    error_message = f"Error processing response: {str(e)}"
                    st.warning(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": {"error": error_message, "raw_response": response if response else "No response received"}})
                    
                    with chat_container:
                        with st.chat_message("assistant"):
                            st.warning(error_message)
                            st.markdown("Raw response:")
                            st.markdown(response if response else "No response received")
                
                except requests.exceptions.HTTPError as e:
                    error_message = ""
                    if e.response.status_code == 429:
                        error_message = "Rate limit reached. Please try again after some time."
                    elif e.response.status_code == 400:
                        error_message = "Invalid request: There was an issue with the format or content of your request."
                    elif e.response.status_code == 401:
                        error_message = "Authentication error: There's an issue with your API key."
                    elif e.response.status_code == 403:
                        error_message = "Permission error: Your API key does not have permission to use the specified resource."
                    elif e.response.status_code == 404:
                        error_message = "Not found: The requested resource was not found."
                    elif e.response.status_code == 413:
                        error_message = "Request too large: Request exceeds the maximum allowed number of bytes."
                    elif e.response.status_code == 500:
                        error_message = "API error: An unexpected error has occurred internal to Anthropic's systems."
                    elif e.response.status_code == 529:
                        error_message = "Overloaded error: Anthropic's API is temporarily overloaded."
                    else:
                        error_message = f"HTTP Error: {str(e)}"
                    
                    st.warning(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": {"error": error_message}})

                except Exception as e:
                    error_message = str(e)
                    if "429" in error_message:
                        error_message = "Rate limit reached. Please try again after some time."
                    elif "400" in error_message:
                        error_message = "Invalid request: There was an issue with the format or content of your request."
                    elif "401" in error_message:
                        error_message = "Authentication error: There's an issue with your API key."
                    elif "403" in error_message:
                        error_message = "Permission error: Your API key does not have permission to use the specified resource."
                    elif "404" in error_message:
                        error_message = "Not found: The requested resource was not found."
                    elif "413" in error_message:
                        error_message = "Request too large: Request exceeds the maximum allowed number of bytes."
                    elif "500" in error_message:
                        error_message = "API error: An unexpected error has occurred internal to Anthropic's systems."
                    elif "529" in error_message:
                        error_message = "Overloaded error: Anthropic's API is temporarily overloaded."
                    else:
                        error_message = f"An unexpected error occurred: {error_message}"
                    
                    st.warning(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": {"error": error_message}})

        spinner_placeholder.empty()

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
                    compliance_checker.load_matrix(sotr_matrix)
                elif isinstance(sotr_file, bytes):
                    compliance_checker.load_matrix(sotr_file.getvalue())
                else:
                    st.error("Unsupported SOTR matrix type")
                    return
                
                if isinstance(tender_document, str):
                    compliance_checker.load_tender(tender_document)
                elif isinstance(tender_document, bytes):
                    compliance_checker.load_tender(tender_document)
                else:
                    st.error("Unsupported tender document type")
                    return
                
                compliance_results = compliance_checker.check_compliance()

                st.write("Compliance Check Results:")
                st.data_editor(compliance_results.style.apply(color_rows, axis=1), hide_index=True)

def color_rows(row):
    color_map = {
        'Yes': 'background-color: #006400',
        'Partial': 'background-color: #8B8000',
        'No': 'background-color: #8B0000'
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