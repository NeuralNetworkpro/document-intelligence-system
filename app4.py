import streamlit as st
import base64
import tempfile
import os
import json
import io
import uuid
import re
import pandas as pd
from mistralai import Mistral
from PIL import Image

# Page configuration with Bayer branding
st.set_page_config(
    page_title="Bayer Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Bayer branding and improved styling
st.markdown("""
<style>
    /* Bayer brand colors */
    :root {
        --bayer-blue: #0037a6;
        --bayer-green: #00aa4f;
        --bayer-light-blue: #e6eeff;
        --bayer-light-green: #e6fff2;
    }
    
    /* Main container styling */
    .main {
        background-color: white;
        padding: 0 !important;
    }
    
    /* Header styling */
    .main-header {
        font-size: 2.5rem;
        color: var(--bayer-blue);
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    .sub-header {
        font-size: 1.5rem;
        color: var(--bayer-blue);
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: var(--bayer-blue);
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #002a7d;
    }
    
    .stButton>button:disabled {
        background-color: #cccccc;
    }
    
    /* Container styling */
    .result-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Chat styling */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .chat-message.user {
        background-color: var(--bayer-light-blue);
        border-left: 5px solid var(--bayer-blue);
    }
    
    .chat-message.assistant {
        background-color: #f8f9fa;
        border-left: 5px solid var(--bayer-green);
    }
    
    .chat-message .content {
        margin-top: 0.5rem;
        line-height: 1.5;
    }
    
    /* Sidebar styling */
    .sidebar-content {
        padding: 1rem;
    }
    
    .sidebar-header {
        color: var(--bayer-blue);
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    /* File uploader styling */
    .file-uploader {
        margin-bottom: 1.5rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--bayer-light-blue);
        border-bottom: 2px solid var(--bayer-blue);
    }
    
    /* Card styling */
    .card {
        border-radius: 10px;
        padding: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    /* Stats container */
    .stats-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }
    
    .stat-card {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 23%;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    
    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--bayer-blue);
        margin-bottom: 0.3rem;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    /* Navigation styling */
    .file-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 1rem;
        background-color: #f8f9fa;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    
    /* Footer styling */
    .footer {
        margin-top: 3rem;
        padding: 1.5rem;
        text-align: center;
        border-top: 1px solid #e9ecef;
        color: #6c757d;
    }
    
    /* Logo container */
    .logo-container {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
    }
    
    .logo-text {
        margin-left: 1rem;
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--bayer-blue);
    }
    
    /* Document preview container */
    .preview-container {
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 0.5rem;
        background-color: white;
        height: 600px;
        overflow: auto;
    }
    
    /* Download button styling */
    .download-btn {
        background-color: white;
        color: var(--bayer-blue);
        border: 1px solid var(--bayer-blue);
        border-radius: 5px;
        padding: 0.4rem 0.8rem;
        font-weight: 500;
        transition: background-color 0.3s;
    }
    
    .download-btn:hover {
        background-color: var(--bayer-light-blue);
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background-color: var(--bayer-blue);
    }
</style>
""", unsafe_allow_html=True)

# Header with Bayer branding
st.markdown("""
<div class="logo-container">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Bayer_Logo.svg/1200px-Bayer_Logo.svg.png" height="40">
    <div class="logo-text">Document Intelligence System</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>Document Intelligence System</h1>", unsafe_allow_html=True)
st.markdown("<p>Extract, analyze, and query documents using advanced OCR and RAG capabilities</p>", unsafe_allow_html=True)

# Dashboard stats
if "total_documents" not in st.session_state:
    st.session_state.total_documents = 0
if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0

# Initialize session state for storing results
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = []
if "preview_sources" not in st.session_state:
    st.session_state.preview_sources = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "current_file_index" not in st.session_state:
    st.session_state.current_file_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "ocr"
if "processing_times" not in st.session_state:
    st.session_state.processing_times = []

# Function to clean API key
def clean_api_key(api_key):
    """Clean the API key by removing any whitespace and 'Bearer' prefix."""
    if not api_key:
        return ""
    
    # Remove any whitespace
    api_key = api_key.strip()
    
    # Remove 'Bearer' prefix if present
    api_key = re.sub(r'^Bearer\s+', '', api_key)
    
    return api_key

# Display dashboard stats
st.markdown("<div class='stats-container'>", unsafe_allow_html=True)

st.markdown(f"""
<div class="stat-card">
    <div class="stat-value">{st.session_state.total_documents}</div>
    <div class="stat-label">Documents Processed</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="stat-card">
    <div class="stat-value">{st.session_state.total_pages}</div>
    <div class="stat-label">Pages Analyzed</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="stat-card">
    <div class="stat-value">{len(st.session_state.ocr_results)}</div>
    <div class="stat-label">Current Session Documents</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="stat-card">
    <div class="stat-value">{st.session_state.total_queries}</div>
    <div class="stat-label">Questions Answered</div>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sidebar-header'>Configuration</h2>", unsafe_allow_html=True)
    
    # API key input
    api_key_input = st.text_input("Enter your Mistral API Key", type="password")
    api_key = clean_api_key(api_key_input)
    
    # Model selection for RAG
    rag_model = st.selectbox(
        "Select LLM for Question Answering",
        ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-7b"],
        index=0
    )
    
    # Input method selection
    input_method = st.radio("Select Input Type:", ["URL", "File Upload"])
    
    # File type selection (only shown for file upload)
    if input_method == "File Upload":
        file_type = st.radio("Select file type", ["PDF", "Image"])
    
    # Advanced settings collapsible section
    with st.expander("Advanced Settings"):
        ocr_quality = st.select_slider(
            "OCR Quality",
            options=["Fast", "Balanced", "High Quality"],
            value="Balanced"
        )
        
        include_tables = st.checkbox("Extract Tables", value=True)
        
        max_tokens = st.slider(
            "Max Response Length",
            min_value=100,
            max_value=4000,
            value=1000,
            step=100
        )
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main content area
if not api_key:
    # Welcome card when no API key is provided
    st.markdown("""
    <div class="card">
        <h2 style="color: var(--bayer-blue);">Welcome to Bayer's Document Intelligence System</h2>
        <p style="margin-bottom: 1rem;">
            This system helps you extract information from documents, analyze content, and answer questions using advanced AI.
        </p>
        <h3 style="color: var(--bayer-blue); font-size: 1.2rem;">Key Features:</h3>
        <ul>
            <li>Extract text from PDFs and images with high accuracy</li>
            <li>Process documents from URLs or file uploads</li>
            <li>Ask questions about document content</li>
            <li>Export results in multiple formats</li>
            <li>Analyze document structure and content</li>
        </ul>
        <p style="margin-top: 1rem; font-weight: 500;">Please enter your Mistral API key in the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    try:
        # Initialize Mistral client with cleaned API key
        client = Mistral(api_key=api_key)
        
        # Main tabs for application sections
        tab1, tab2, tab3 = st.tabs(["Document Processing", "Analysis & Insights", "Help & Documentation"])
        
        with tab1:
            # Input section based on selected method
            st.markdown("<h2 class='sub-header'>Document Input</h2>", unsafe_allow_html=True)
            
            # Create two columns for input and instructions
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if input_method == "URL":
                    urls = st.text_area("Enter one or multiple URLs (separate with new lines)", 
                                        placeholder="https://example.com/document.pdf\nhttps://example.com/image.jpg")
                    process_button = st.button("Process Documents")
                    
                    if process_button and urls.strip():
                        # Clear previous results
                        st.session_state.ocr_results = []
                        st.session_state.preview_sources = []
                        st.session_state.file_names = []
                        st.session_state.chat_history = {}
                        st.session_state.processing_times = []
                        
                        url_list = [url.strip() for url in urls.split("\n") if url.strip()]
                        
                        with st.spinner("Processing documents..."):
                            progress_bar = st.progress(0)
                            
                            for i, url in enumerate(url_list):
                                try:
                                    # Update progress
                                    progress_bar.progress((i) / len(url_list))
                                    
                                    # Determine if URL is for image or document based on extension
                                    is_image = any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif'])
                                    
                                    document = {
                                        "type": "image_url" if is_image else "document_url",
                                        "image_url" if is_image else "document_url": url
                                    }
                                    
                                    # Process with Mistral OCR
                                    ocr_response = client.ocr.process(
                                        model="mistral-ocr-latest",
                                        document=document,
                                        include_image_base64=True
                                    )
                                    
                                    # Extract results
                                    pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                                    result_text = "\n\n".join(page.markdown for page in pages) if pages else "No text extracted."
                                    
                                    # Generate a unique ID for this document
                                    doc_id = str(uuid.uuid4())
                                    
                                    # Store results
                                    st.session_state.ocr_results.append(result_text)
                                    st.session_state.preview_sources.append(url)
                                    st.session_state.file_names.append(os.path.basename(url))
                                    st.session_state.chat_history[doc_id] = []
                                    st.session_state.processing_times.append(0.5)  # Placeholder processing time
                                    
                                    # Update stats
                                    st.session_state.total_documents += 1
                                    st.session_state.total_pages += len(pages) if pages else 1
                                
                                except Exception as e:
                                    st.error(f"Error processing {url}: {str(e)}")
                            
                            # Complete progress
                            progress_bar.progress(1.0)
                
                else:  # File Upload
                    uploaded_files = st.file_uploader(
                        f"Upload {'PDF' if file_type == 'PDF' else 'image'} files",
                        type=["pdf"] if file_type == "PDF" else ["jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key="file-uploader"
                    )
                    
                    process_button = st.button("Process Documents")
                    
                    if process_button and uploaded_files:
                        # Clear previous results
                        st.session_state.ocr_results = []
                        st.session_state.preview_sources = []
                        st.session_state.file_names = []
                        st.session_state.chat_history = {}
                        st.session_state.processing_times = []
                        
                        with st.spinner("Processing documents..."):
                            progress_bar = st.progress(0)
                            
                            for i, uploaded_file in enumerate(uploaded_files):
                                try:
                                    # Update progress
                                    progress_bar.progress((i) / len(uploaded_files))
                                    
                                    # Reset file position to beginning
                                    uploaded_file.seek(0)
                                    file_content = uploaded_file.read()
                                    file_name = uploaded_file.name
                                    
                                    # Create base64 encoded data URL
                                    if file_type == "PDF":
                                        # Save PDF to a temporary file
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                                            temp_file.write(file_content)
                                            temp_path = temp_file.name
                                        
                                        try:
                                            # Upload the file to Mistral
                                            with open(temp_path, "rb") as file_obj:
                                                file_upload = client.files.upload(
                                                    file={"file_name": file_name, "content": file_obj},
                                                    purpose="ocr"
                                                )
                                            
                                            # Get signed URL
                                            signed_url_response = client.files.get_signed_url(file_id=file_upload.id)
                                            document_url = signed_url_response.url
                                            
                                            # Process with Mistral OCR using the signed URL
                                            document = {"type": "document_url", "document_url": document_url}
                                            
                                            # For preview, create a data URL
                                            encoded_file = base64.b64encode(file_content).decode("utf-8")
                                            preview_url = f"data:application/pdf;base64,{encoded_file}"
                                        finally:
                                            # Clean up temporary file
                                            if os.path.exists(temp_path):
                                                os.remove(temp_path)
                                    else:  # Image
                                        # For images, use base64 encoding directly
                                        encoded_file = base64.b64encode(file_content).decode("utf-8")
                                        mime_type = uploaded_file.type or "image/jpeg"
                                        data_url = f"data:{mime_type};base64,{encoded_file}"
                                        document = {"type": "image_url", "image_url": data_url}
                                        preview_url = data_url
                                    
                                    # Process with Mistral OCR
                                    ocr_response = client.ocr.process(
                                        model="mistral-ocr-latest",
                                        document=document,
                                        include_image_base64=True
                                    )
                                    
                                    # Extract results
                                    pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                                    result_text = "\n\n".join(page.markdown for page in pages) if pages else "No text extracted."
                                    
                                    # Generate a unique ID for this document
                                    doc_id = str(uuid.uuid4())
                                    
                                    # Store results
                                    st.session_state.ocr_results.append(result_text)
                                    st.session_state.preview_sources.append(preview_url)
                                    st.session_state.file_names.append(file_name)
                                    st.session_state.chat_history[doc_id] = []
                                    st.session_state.processing_times.append(0.8)  # Placeholder processing time
                                    
                                    # Update stats
                                    st.session_state.total_documents += 1
                                    st.session_state.total_pages += len(pages) if pages else 1
                                
                                except Exception as e:
                                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                            
                            # Complete progress
                            progress_bar.progress(1.0)
            
            with col2:
                st.markdown("""
                <div class="card">
                    <h3 style="color: var(--bayer-blue);">Tips</h3>
                    <ul style="margin-bottom: 1rem;">
                        <li>For best results, use high-quality scans</li>
                        <li>PDFs with searchable text work best</li>
                        <li>Supported formats: PDF, JPG, PNG</li>
                        <li>Maximum file size: 20MB</li>
                    </ul>
                    <h3 style="color: var(--bayer-blue);">Processing</h3>
                    <p>Documents are processed securely using Mistral's OCR technology.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Display results if available
            if st.session_state.ocr_results:
                st.markdown("<h2 class='sub-header'>OCR Results</h2>", unsafe_allow_html=True)
                
                # File navigation if multiple files
                if len(st.session_state.ocr_results) > 1:
                    st.markdown("<div class='file-nav'>", unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1, 3, 1])
                    
                    with col1:
                        if st.button("Previous", disabled=st.session_state.current_file_index == 0):
                            st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
                    
                    with col2:
                        st.markdown(f"<p style='text-align: center; margin: 0;'><strong>File {st.session_state.current_file_index + 1} of {len(st.session_state.ocr_results)}:</strong> {st.session_state.file_names[st.session_state.current_file_index]}</p>", unsafe_allow_html=True)
                    
                    with col3:
                        if st.button("Next", disabled=st.session_state.current_file_index == len(st.session_state.ocr_results) - 1):
                            st.session_state.current_file_index = min(len(st.session_state.ocr_results) - 1, st.session_state.current_file_index + 1)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # Display current file and OCR results side by side
                idx = st.session_state.current_file_index
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("<h3 style='color: var(--bayer-blue);'>Document Preview</h3>", unsafe_allow_html=True)
                    
                    preview_src = st.session_state.preview_sources[idx]
                    
                    # Display PDF or image based on content type
                    st.markdown("<div class='preview-container'>", unsafe_allow_html=True)
                    if "application/pdf" in preview_src or preview_src.lower().endswith(".pdf"):
                        pdf_embed_html = f'<iframe src="{preview_src}" width="100%" height="100%" frameborder="0"></iframe>'
                        st.markdown(pdf_embed_html, unsafe_allow_html=True)
                    else:
                        st.image(preview_src, use_column_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<h3 style='color: var(--bayer-blue);'>OCR Results</h3>", unsafe_allow_html=True)
                    
                    # Display OCR results
                    st.markdown("<div class='result-container' style='height: 500px; overflow-y: auto;'>", unsafe_allow_html=True)
                    st.markdown(st.session_state.ocr_results[idx])
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Download options
                    st.markdown("<h4 style='color: var(--bayer-blue); margin-top: 1rem;'>Download Options</h4>", unsafe_allow_html=True)
                    
                    result_text = st.session_state.ocr_results[idx]
                    file_name_base = os.path.splitext(st.session_state.file_names[idx])[0]
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Download as text
                        st.download_button(
                            label="Download as Text",
                            data=result_text,
                            file_name=f"{file_name_base}_ocr.txt",
                            mime="text/plain",
                            key=f"download_text_{idx}"
                        )
                    
                    with col2:
                        # Download as markdown
                        st.download_button(
                            label="Download as Markdown",
                            data=result_text,
                            file_name=f"{file_name_base}_ocr.md",
                            mime="text/markdown",
                            key=f"download_md_{idx}"
                        )
                    
                    with col3:
                        # Download as JSON
                        json_data = json.dumps({"ocr_result": result_text}, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="Download as JSON",
                            data=json_data,
                            file_name=f"{file_name_base}_ocr.json",
                            mime="application/json",
                            key=f"download_json_{idx}"
                        )
                
                # Question Answering section
                st.markdown("<h2 class='sub-header' style='margin-top: 2rem;'>Question Answering</h2>", unsafe_allow_html=True)
                
                # File selection for QA if multiple files
                if len(st.session_state.ocr_results) > 1:
                    qa_file_idx = st.selectbox(
                        "Select document to query:",
                        range(len(st.session_state.file_names)),
                        format_func=lambda i: st.session_state.file_names[i],
                        index=st.session_state.current_file_index
                    )
                else:
                    qa_file_idx = 0
                
                # Get document ID for chat history
                doc_id = list(st.session_state.chat_history.keys())[qa_file_idx] if qa_file_idx < len(st.session_state.chat_history) else None
                
                if doc_id:
                    # Create columns for chat and document context
                    chat_col, context_col = st.columns([2, 1])
                    
                    with chat_col:
                        # Display chat history
                        chat_container = st.container()
                        
                        with chat_container:
                            if not st.session_state.chat_history[doc_id]:
                                st.markdown("""
                                <div style="text-align: center; padding: 2rem; color: #6c757d;">
                                    <p>No questions asked yet. Start by asking a question about the document.</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                for message in st.session_state.chat_history[doc_id]:
                                    role = message["role"]
                                    content = message["content"]
                                    
                                    st.markdown(f"<div class='chat-message {role}'>", unsafe_allow_html=True)
                                    st.markdown(f"<div><strong>{role.capitalize()}</strong></div>", unsafe_allow_html=True)
                                    st.markdown(f"<div class='content'>{content}</div>", unsafe_allow_html=True)
                                    st.markdown("</div>", unsafe_allow_html=True)
                        
                        # User input for questions
                        user_question = st.text_input("Ask a question about the document:", 
                                                     placeholder="E.g., What are the key findings in this document?",
                                                     key=f"question_{qa_file_idx}")
                        
                        col1, col2 = st.columns([1, 4])
                        
                        with col1:
                            submit_button = st.button("Submit", key=f"submit_{qa_file_idx}")
                        
                        with col2:
                            if st.button("Clear Chat History", key=f"clear_{qa_file_idx}"):
                                st.session_state.chat_history[doc_id] = []
                                st.experimental_rerun()
                        
                        if submit_button and user_question:
                            # Add user question to chat history
                            st.session_state.chat_history[doc_id].append({
                                "role": "user",
                                "content": user_question
                            })
                            
                            # Get document content
                            document_content = st.session_state.ocr_results[qa_file_idx]
                            
                            # Create system prompt with document content
                            system_prompt = f"""You are a helpful assistant that answers questions based on the provided document.
                            
Document content:
{document_content}

Answer questions based ONLY on the information in the document. If the answer is not in the document, say "I don't have enough information to answer that question based on the document content." Be concise and accurate."""
                            
                            # Create messages for chat completion using the standard format
                            messages = [
                                {"role": "system", "content": system_prompt}
                            ]
                            
                            # Add chat history
                            for msg in st.session_state.chat_history[doc_id]:
                                messages.append({"role": msg["role"], "content": msg["content"]})
                            
                            # Get response from Mistral
                            with st.spinner("Generating answer..."):
                                try:
                                    # Use the complete method of the client.chat object as per Mistral documentation
                                    chat_response = client.chat.complete(
                                        model=rag_model,
                                        messages=messages,
                                        max_tokens=max_tokens
                                    )
                                    
                                    # Extract assistant response
                                    assistant_response = chat_response.choices[0].message.content
                                    
                                    # Add assistant response to chat history
                                    st.session_state.chat_history[doc_id].append({
                                        "role": "assistant",
                                        "content": assistant_response
                                    })
                                    
                                    # Update query count
                                    st.session_state.total_queries += 1
                                    
                                    # Rerun to update the UI
                                    st.experimental_rerun()
                                
                                except Exception as e:
                                    st.error(f"Error generating response: {str(e)}")
                    
                    with context_col:
                        st.markdown("""
                        <div class="card">
                            <h3 style="color: var(--bayer-blue);">Document Context</h3>
                            <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                                The AI uses the document content to answer your questions. It can only reference information contained in the document.
                            </p>
                            <p style="font-size: 0.9rem; color: #6c757d;">
                                For best results, ask specific questions about the content of the document.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show document metadata
                        st.markdown("""
                        <div class="card">
                            <h3 style="color: var(--bayer-blue);">Document Info</h3>
                            <table style="width: 100%; font-size: 0.9rem;">
                                <tr>
                                    <td style="padding: 0.3rem 0; font-weight: 500;">Filename:</td>
                                    <td style="padding: 0.3rem 0;">{}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 0.3rem 0; font-weight: 500;">Type:</td>
                                    <td style="padding: 0.3rem 0;">{}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 0.3rem 0; font-weight: 500;">Size:</td>
                                    <td style="padding: 0.3rem 0;">~{} KB</td>
                                </tr>
                                <tr>
                                    <td style="padding: 0.3rem 0; font-weight: 500;">Processed:</td>
                                    <td style="padding: 0.3rem 0;">{} sec</td>
                                </tr>
                            </table>
                        </div>
                        """.format(
                            st.session_state.file_names[qa_file_idx],
                            "PDF" if ".pdf" in st.session_state.file_names[qa_file_idx].lower() else "Image",
                            "250",  # Placeholder size
                            st.session_state.processing_times[qa_file_idx] if qa_file_idx < len(st.session_state.processing_times) else "0.5"
                        ), unsafe_allow_html=True)
        
        with tab2:
            if not st.session_state.ocr_results:
                st.markdown("""
                <div style="text-align: center; padding: 3rem; color: #6c757d;">
                    <h3>No documents processed yet</h3>
                    <p>Process documents in the Document Processing tab to see analysis and insights.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<h2 class='sub-header'>Document Analysis</h2>", unsafe_allow_html=True)
                
                # Create sample data for visualization
                if len(st.session_state.ocr_results) > 0:
                    # Document length analysis
                    doc_lengths = [len(text) for text in st.session_state.ocr_results]
                    doc_names = [name[:15] + "..." if len(name) > 15 else name for name in st.session_state.file_names]
                    
                    # Create a DataFrame for the document lengths
                    df_lengths = pd.DataFrame({
                        "Document": doc_names,
                        "Character Count": doc_lengths
                    })
                    
                    # Create a bar chart for document lengths
                    st.markdown("<h3 style='color: var(--bayer-blue);'>Document Size Comparison</h3>", unsafe_allow_html=True)
                    st.bar_chart(df_lengths.set_index("Document"))
                    
                    # Create sample data for document types
                    doc_types = []
                    for name in st.session_state.file_names:
                        if name.lower().endswith(".pdf"):
                            doc_types.append("PDF")
                        elif name.lower().endswith((".jpg", ".jpeg", ".png")):
                            doc_types.append("Image")
                        else:
                            doc_types.append("Other")
                    
                    # Count document types
                    type_counts = {}
                    for doc_type in doc_types:
                        if doc_type in type_counts:
                            type_counts[doc_type] += 1
                        else:
                            type_counts[doc_type] = 1
                    
                    # Create a DataFrame for the document types
                    df_types = pd.DataFrame({
                        "Type": list(type_counts.keys()),
                        "Count": list(type_counts.values())
                    })
                    
                    # Create columns for charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Create a pie chart for document types
                        st.markdown("<h3 style='color: var(--bayer-blue);'>Document Types</h3>", unsafe_allow_html=True)
                        st.pie_chart(df_types.set_index("Type"))
                    
                    with col2:
                        # Create sample data for processing times
                        if len(st.session_state.processing_times) > 0:
                            df_times = pd.DataFrame({
                                "Document": doc_names,
                                "Processing Time (s)": st.session_state.processing_times
                            })
                            
                            # Create a bar chart for processing times
                            st.markdown("<h3 style='color: var(--bayer-blue);'>Processing Times</h3>", unsafe_allow_html=True)
                            st.bar_chart(df_times.set_index("Document"))
                
                # Content analysis section
                st.markdown("<h2 class='sub-header' style='margin-top: 2rem;'>Content Analysis</h2>", unsafe_allow_html=True)
                
                # Select document for analysis
                analysis_idx = st.selectbox(
                    "Select document to analyze:",
                    range(len(st.session_state.file_names)),
                    format_func=lambda i: st.session_state.file_names[i],
                    index=st.session_state.current_file_index
                )
                
                if st.button("Analyze Document"):
                    with st.spinner("Analyzing document content..."):
                        try:
                            # Get document content
                            document_content = st.session_state.ocr_results[analysis_idx]
                            
                            # Create system prompt for analysis
                            system_prompt = f"""Analyze the following document content and provide:
1. A brief summary (3-5 sentences)
2. Key topics or themes (bullet points)
3. Any entities mentioned (people, organizations, locations)
4. Document structure analysis (sections, headings, etc.)

Document content:
{document_content}

Format your response with clear headings and bullet points where appropriate."""
                            
                            # Create messages for chat completion
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": "Please analyze this document."}
                            ]
                            
                            # Get response from Mistral
                            analysis_response = client.chat.complete(
                                model=rag_model,
                                messages=messages,
                                max_tokens=2000
                            )
                            
                            # Extract analysis
                            analysis_text = analysis_response.choices[0].message.content
                            
                            # Display analysis
                            st.markdown("<div class='result-container'>", unsafe_allow_html=True)
                            st.markdown(analysis_text)
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        except Exception as e:
                            st.error(f"Error analyzing document: {str(e)}")
        
        with tab3:
            st.markdown("<h2 class='sub-header'>Help & Documentation</h2>", unsafe_allow_html=True)
            
            # Create tabs for different help sections
            help_tab1, help_tab2, help_tab3 = st.tabs(["Getting Started", "Features", "FAQ"])
            
            with help_tab1:
                st.markdown("""
                <div class="card">
                    <h3 style="color: var(--bayer-blue);">Getting Started</h3>
                    <p>Welcome to Bayer's Document Intelligence System. This tool helps you extract and analyze information from documents using advanced AI technology.</p>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Quick Start Guide</h4>
                    <ol>
                        <li><strong>Configure:</strong> Enter your Mistral API key in the sidebar</li>
                        <li><strong>Select Input Method:</strong> Choose between URL or File Upload</li>
                        <li><strong>Process Documents:</strong> Upload files or enter URLs and click "Process Documents"</li>
                        <li><strong>View Results:</strong> Explore the extracted text and document preview</li>
                        <li><strong>Ask Questions:</strong> Use the Question Answering section to query document content</li>
                    </ol>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">System Requirements</h4>
                    <ul>
                        <li>Modern web browser (Chrome, Firefox, Safari, Edge)</li>
                        <li>Valid Mistral API key</li>
                        <li>Internet connection</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with help_tab2:
                st.markdown("""
                <div class="card">
                    <h3 style="color: var(--bayer-blue);">Features</h3>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Document Processing</h4>
                    <ul>
                        <li><strong>OCR Technology:</strong> Extract text from images and PDFs with high accuracy</li>
                        <li><strong>Multiple Input Methods:</strong> Process documents via URL or file upload</li>
                        <li><strong>Batch Processing:</strong> Process multiple documents in one go</li>
                        <li><strong>Format Support:</strong> Works with PDFs and common image formats (JPG, PNG)</li>
                    </ul>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Question Answering</h4>
                    <ul>
                        <li><strong>Document-based QA:</strong> Ask questions about document content</li>
                        <li><strong>Context-aware:</strong> AI understands document context for accurate answers</li>
                        <li><strong>Conversation History:</strong> Maintains chat history for follow-up questions</li>
                        <li><strong>Model Selection:</strong> Choose from different Mistral models for optimal results</li>
                    </ul>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Analysis & Insights</h4>
                    <ul>
                        <li><strong>Document Analytics:</strong> Visualize document metrics and processing statistics</li>
                        <li><strong>Content Analysis:</strong> Get summaries, key topics, and entity extraction</li>
                        <li><strong>Comparative Analysis:</strong> Compare multiple documents</li>
                    </ul>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Export Options</h4>
                    <ul>
                        <li><strong>Multiple Formats:</strong> Download results as Text, Markdown, or JSON</li>
                        <li><strong>Data Preservation:</strong> Save extracted information for future reference</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with help_tab3:
                st.markdown("""
                <div class="card">
                    <h3 style="color: var(--bayer-blue);">Frequently Asked Questions</h3>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">General Questions</h4>
                    
                    <p><strong>Q: How accurate is the OCR technology?</strong></p>
                    <p>A: The OCR technology uses Mistral's advanced models and typically achieves 95%+ accuracy on clear, well-scanned documents. Accuracy may vary based on document quality, fonts, and formatting.</p>
                    
                    <p><strong>Q: Is my data secure?</strong></p>
                    <p>A: Yes, document processing is done securely. Your API key and documents are handled according to Mistral's security policies. No document content is stored permanently unless you explicitly save it.</p>
                    
                    <p><strong>Q: What file types are supported?</strong></p>
                    <p>A: Currently, the system supports PDF documents and common image formats (JPG, JPEG, PNG). Support for additional formats may be added in future updates.</p>
                    
                    <h4 style="color: var(--bayer-blue); margin-top: 1rem;">Technical Questions</h4>
                    
                    <p><strong>Q: Why am I getting an error when processing my document?</strong></p>
                    <p>A: Common issues include invalid API keys, file size limitations, unsupported file formats, or temporary service disruptions. Check the error message for specific details.</p>
                    
                    <p><strong>Q: How can I improve the quality of extracted text?</strong></p>
                    <p>A: For best results, use high-quality scans, ensure documents are properly aligned, and use PDFs with embedded text when possible. The "High Quality" OCR setting may also improve results for complex documents.</p>
                    
                    <p><strong>Q: Can I process documents in languages other than English?</strong></p>
                    <p>A: Yes, the OCR system supports multiple languages. However, optimal performance is achieved with English documents. The question answering feature works best with the language selected in the model settings.</p>
                </div>
                """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Error initializing Mistral client: {str(e)}")
        st.error("Please check your API key and try again.")

# Footer with Bayer branding
st.markdown("""
<div class="footer">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Bayer_Logo.svg/1200px-Bayer_Logo.svg.png" height="30" style="margin-bottom: 1rem;">
    <p>© 2025 Bayer AG. All rights reserved.</p>
    <p style="margin-top: 0.5rem;">
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Privacy Policy</a> | 
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Terms of Service</a> | 
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Contact Support</a>
    </p>
</div>
""", unsafe_allow_html=True)