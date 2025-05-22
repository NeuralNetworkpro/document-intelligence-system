import streamlit as st
import base64
import tempfile
import os
import json
import io
from mistralai import Mistral
from PIL import Image

# Page configuration with improved styling
st.set_page_config(
    page_title="Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4F8BF9;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4F8BF9;
        margin-bottom: 0.5rem;
    }
    .stButton>button {
        background-color: #4F8BF9;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #3670CC;
    }
    .result-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .download-btn {
        margin-top: 1rem;
    }
    .sidebar-content {
        padding: 1rem;
    }
    .file-uploader {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# App title with custom styling
st.markdown("<h1 class='main-header'>Document Intelligence System</h1>", unsafe_allow_html=True)
st.markdown("<p>Extract and analyze text from documents using advanced OCR capabilities</p>", unsafe_allow_html=True)

# Initialize session state for storing results
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = []
if "preview_sources" not in st.session_state:
    st.session_state.preview_sources = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "current_file_index" not in st.session_state:
    st.session_state.current_file_index = 0

# Sidebar for configuration
with st.sidebar:
    st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>Configuration</h2>", unsafe_allow_html=True)
    
    # API key input
    api_key = st.text_input("Enter your Mistral API Key", type="password")
    
    # Input method selection
    input_method = st.radio("Select Input Type:", ["URL", "File Upload"])
    
    # File type selection (only shown for file upload)
    if input_method == "File Upload":
        file_type = st.radio("Select file type", ["PDF", "Image"])
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main content area
if not api_key:
    st.warning("Please enter your API key in the sidebar to continue.")
else:
    # Initialize Mistral client
    client = Mistral(api_key=api_key)
    
    # Input section based on selected method
    if input_method == "URL":
        urls = st.text_area("Enter one or multiple URLs (separate with new lines)")
        process_button = st.button("Process URLs")
        
        if process_button and urls.strip():
            # Clear previous results
            st.session_state.ocr_results = []
            st.session_state.preview_sources = []
            st.session_state.file_names = []
            
            url_list = [url.strip() for url in urls.split("\n") if url.strip()]
            
            with st.spinner("Processing documents..."):
                for url in url_list:
                    try:
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
                        
                        # Store results
                        st.session_state.ocr_results.append(result_text)
                        st.session_state.preview_sources.append(url)
                        st.session_state.file_names.append(os.path.basename(url))
                    
                    except Exception as e:
                        st.error(f"Error processing {url}: {str(e)}")
    
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
            
            with st.spinner("Processing documents..."):
                for uploaded_file in uploaded_files:
                    try:
                        file_content = uploaded_file.read()
                        file_name = uploaded_file.name
                        
                        # Create base64 encoded data URL
                        if file_type == "PDF":
                            encoded_file = base64.b64encode(file_content).decode("utf-8")
                            data_url = f"data:application/pdf;base64,{encoded_file}"
                            document = {"type": "document_url", "document_url": data_url}
                        else:  # Image
                            encoded_file = base64.b64encode(file_content).decode("utf-8")
                            mime_type = uploaded_file.type or "image/jpeg"
                            data_url = f"data:{mime_type};base64,{encoded_file}"
                            document = {"type": "image_url", "image_url": data_url}
                        
                        # Process with Mistral OCR
                        ocr_response = client.ocr.process(
                            model="mistral-ocr-latest",
                            document=document,
                            include_image_base64=True
                        )
                        
                        # Extract results
                        pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                        result_text = "\n\n".join(page.markdown for page in pages) if pages else "No text extracted."
                        
                        # Store results
                        st.session_state.ocr_results.append(result_text)
                        st.session_state.preview_sources.append(data_url)
                        st.session_state.file_names.append(file_name)
                    
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    # Display results if available
    if st.session_state.ocr_results:
        st.markdown("<h2 class='sub-header'>Results</h2>", unsafe_allow_html=True)
        
        # File navigation if multiple files
        if len(st.session_state.ocr_results) > 1:
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("Previous", disabled=st.session_state.current_file_index == 0):
                    st.session_state.current_file_index = max(0, st.session_state.current_file_index - 1)
            
            with col2:
                st.markdown(f"<p style='text-align: center;'>File {st.session_state.current_file_index + 1} of {len(st.session_state.ocr_results)}: {st.session_state.file_names[st.session_state.current_file_index]}</p>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Next", disabled=st.session_state.current_file_index == len(st.session_state.ocr_results) - 1):
                    st.session_state.current_file_index = min(len(st.session_state.ocr_results) - 1, st.session_state.current_file_index + 1)
        
        # Display current file and OCR results side by side
        idx = st.session_state.current_file_index
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<h3>Document Preview</h3>", unsafe_allow_html=True)
            
            preview_src = st.session_state.preview_sources[idx]
            
            # Display PDF or image based on content type
            if "application/pdf" in preview_src or preview_src.lower().endswith(".pdf"):
                pdf_embed_html = f'<iframe src="{preview_src}" width="100%" height="600" frameborder="0"></iframe>'
                st.markdown(pdf_embed_html, unsafe_allow_html=True)
            else:
                st.image(preview_src, use_column_width=True)
        
        with col2:
            st.markdown("<h3>OCR Results</h3>", unsafe_allow_html=True)
            
            # Display OCR results
            st.markdown("<div class='result-container'>", unsafe_allow_html=True)
            st.markdown(st.session_state.ocr_results[idx])
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Download options
            st.markdown("<h4>Download Options</h4>", unsafe_allow_html=True)
            
            result_text = st.session_state.ocr_results[idx]
            file_name_base = os.path.splitext(st.session_state.file_names[idx])[0]
            
            col1, col2 = st.columns(2)
            
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
            
            # Download as JSON
            json_data = json.dumps({"ocr_result": result_text}, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download as JSON",
                data=json_data,
                file_name=f"{file_name_base}_ocr.json",
                mime="application/json",
                key=f"download_json_{idx}"
            )

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center;'>Document Intelligence System with OCR capabilities</p>", unsafe_allow_html=True)