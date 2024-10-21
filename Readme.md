# Tender-POC Demo

## 📋 Project Overview

Tender-POC Demo is a Streamlit-based application designed to assist with tender document processing and analysis. It provides features such as SOTR (Statement of Technical Requirements) document handling, tender Q&A, and compliance matrix generation.

## 🚀 Features

- SOTR Document Processing
- Tender Q&A Functionality
- Compliance Matrix Generation
- Streamlit-based User Interface

## 🛠 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/tender-poc.git
   cd tender-poc
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```
## 🖥 Deployment

Follow these steps to deploy the Tender-POC Demo:

1. **Update the Repository**
   ```bash
   git pull origin ui
   ```

2. **Stop Running Instances**
   ```bash
   pm2 kill
   ```

3. **Clean Up Previous Deployments**
   ```bash
   pm2 delete all
   ```

4. **Activate Virtual Environment**
   ```bash
   poetry shell
   ```

5. **Launch the Demo**
   ```bash
   pm2 start --name "tender-poc-streamlit-app" \
             --log-date-format "YYYY-MM-DD HH:mm:ss" \
             -- poetry run python3 -m streamlit run demo.py --server.port 8501
   ```

6. **Monitor Logs (Optional)**
   ```bash
   pm2 logs tender-poc-streamlit-app
   ```