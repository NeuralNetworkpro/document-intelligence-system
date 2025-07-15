
Document Intelligence System
A sophisticated Streamlit application designed to extract, analyze, and validate information from complex documents using advanced OCR and Large Language Model (LLM) capabilities. This tool is optimized for workflows requiring detailed comparison and compliance verification, such as in the pharmaceutical and regulatory industries.

Features
Advanced OCR: Extracts text and structured data from PDF and image files using the Mistral API.

Multi-Document Processing: Upload and analyze a corpus of multiple documents simultaneously.

Interactive Q&A: Engage in a conversation with your documents. Ask specific questions and receive context-aware answers based on the extracted text.

Comprehensive Structured Analysis: Perform a deep-dive analysis across 8 specialized categories (Nutrient, Allergen, Safety, etc.) with a predefined set of expert questions.

Document Compliance Verification:

Compare source documents (like Certificates of Analysis) against a master Excel specification file.

Leverages semantic analysis to intelligently identify matches and mismatches, even when terminology differs.

Provides a detailed, color-coded report for each document, highlighting discrepancies with clear reasoning.

Automated Master File Correction: Automatically generate an updated version of the master Excel file, with mismatched values corrected and all changes highlighted and commented for easy review.

Tabular Data Extraction: Intelligently finds and extracts tables from documents and exports them into a professionally formatted Excel report.

Robust Error Handling: Includes API rate limit handling with exponential backoff to ensure smooth processing of large document batches.

Tech Stack
Backend: Python

Web Framework: Streamlit

AI/LLM: Mistral AI API (for OCR and Chat)

Data Handling: Pandas, Openpyxl

PDF Processing: PyMuPDF

Project Structure
.
├── app.py                  # Main application script (or main.py)
├── comparison.py           # Logic for the document comparison feature
├── masterexcel.py          # Logic for updating the master Excel file
├── tabular.py              # Logic for table extraction and Excel export
├── summary.py              # Logic for the summary/analysis tab
├── updated_questions.py    # Predefined questions for structured analysis
├── requirements.txt        # Project dependencies
└── README.md               # This file

Project Setup & Installation
Follow these steps to set up and run the project locally.

1. Prerequisites
Python 3.9 or higher

pip and venv

2. Clone the Repository
git clone <your-repository-url>
cd <your-repository-directory>

3. Create and Activate a Virtual Environment
On macOS/Linux:

python3 -m venv myenv
source myenv/bin/activate

On Windows:

python -m venv myenv
.\myenv\Scripts\activate

4. Install Dependencies
Install all the required libraries from the requirements.txt file.

pip install -r requirements.txt

5. Set Up Environment Variables
The application requires an API key for the Mistral AI service. You will enter this directly in the application's sidebar UI when you run it. No .env file is needed.

How to Run the Application
Once the setup is complete, you can run the Streamlit application with the following command (assuming your main script is named app.py or main.py):

streamlit run app.py

The application will open in your default web browser.

Using the Application
Configuration: Enter your Mistral API Key in the sidebar.

Process Documents: Select the file type (PDF/Image) and upload one or more source documents. Click "Process Documents" to initiate the OCR extraction.

Navigate Tabs: Once processing is complete, use the tabs to access different features:

Document View: See a preview and the raw text of your documents.

Question Answering: Ask ad-hoc questions about your documents.

Summary: Run a deep-dive, structured analysis based on predefined questions.

Excel Export: Extract all tables into a formatted Excel file.

Comparison: Upload a master Excel file to perform a detailed compliance verification against your source documents. Download a summary report or a corrected version of your master file.

main run file 
old -main.py
new- app.py 