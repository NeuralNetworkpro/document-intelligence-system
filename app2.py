import streamlit as st
import base64
import tempfile
import os
import json
import io
import uuid
import re
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
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #e6f3ff;
        border-left: 5px solid #4F8BF9;
    }
    .chat-message.assistant {
        background-color: #f0f2f6;
        border-left: 5px solid #10a37f;
    }
    .chat-message .content {
        margin-top: 0.5rem;
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
    .tabs-container {
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# App title with custom styling
st.markdown("<h1 class='main-header'>Document Intelligence System</h1>", unsafe_allow_html=True)
st.markdown("<p>Extract, analyze, and query documents using advanced OCR and RAG capabilities</p>", unsafe_allow_html=True)

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

# Sidebar for configuration
with st.sidebar:
    st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>Configuration</h2>", unsafe_allow_html=True)
    
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
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main content area
if not api_key:
    st.warning("Please enter your API key in the sidebar to continue.")
else:
    try:
        # Initialize Mistral client with cleaned API key
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
                st.session_state.chat_history = {}
                
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
                            
                            # Generate a unique ID for this document
                            doc_id = str(uuid.uuid4())
                            
                            # Store results
                            st.session_state.ocr_results.append(result_text)
                            st.session_state.preview_sources.append(url)
                            st.session_state.file_names.append(os.path.basename(url))
                            st.session_state.chat_history[doc_id] = []
                        
                        except Exception as e:
                            st.error(f"Error processing {url}: {str(e)}")
                            st.error(f"Error details: {type(e).__name__}")
        
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
                
                with st.spinner("Processing documents..."):
                    for uploaded_file in uploaded_files:
                        try:
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
                        
                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                            import traceback
                            st.error(f"Traceback: {traceback.format_exc()}")
        
        # Display results if available
        if st.session_state.ocr_results:
            # Tab selection
            tab1, tab2 = st.tabs(["OCR Results", "Question Answering"])
            
            with tab1:
                st.markdown("<h2 class='sub-header'>OCR Results</h2>", unsafe_allow_html=True)
                
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
            
            with tab2:
                st.markdown("<h2 class='sub-header'>Question Answering</h2>", unsafe_allow_html=True)
                
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
                    # Display chat history
                    chat_container = st.container()
                    
                    with chat_container:
                        for message in st.session_state.chat_history[doc_id]:
                            role = message["role"]
                            content = message["content"]
                            
                            st.markdown(f"<div class='chat-message {role}'>", unsafe_allow_html=True)
                            st.markdown(f"<div><strong>{role.capitalize()}</strong></div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='content'>{content}</div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                    
                    # User input for questions
                    user_question = st.text_input("Ask a question about the document:", key=f"question_{qa_file_idx}")
                    
                    if st.button("Submit Question", key=f"submit_{qa_file_idx}"):
                        if user_question:
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
                                        messages=messages
                                    )
                                    
                                    # Extract assistant response
                                    assistant_response = chat_response.choices[0].message.content
                                    
                                    # Add assistant response to chat history
                                    st.session_state.chat_history[doc_id].append({
                                        "role": "assistant",
                                        "content": assistant_response
                                    })
                                    
                                    # Rerun to update the UI
                                    st.experimental_rerun()
                                
                                except Exception as e:
                                    st.error(f"Error generating response: {str(e)}")
                                    import traceback
                                    st.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Option to clear chat history
                    if st.button("Clear Chat History", key=f"clear_{qa_file_idx}"):
                        st.session_state.chat_history[doc_id] = []
                        st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error initializing Mistral client: {str(e)}")
        st.error("Please check your API key and try again.")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center;'>Document Intelligence System with OCR and RAG capabilities</p>", unsafe_allow_html=True)