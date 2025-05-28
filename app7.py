import streamlit as st
import base64
import tempfile
import os
import json
import io
import uuid
import re
import time
from mistralai import Mistral
from PIL import Image

# Import questions from the updated_questions.py file
from updated_questions import (
    NUTRIENT_QUESTIONS,
    DIETARY_QUESTIONS,
    ALLERGEN_QUESTIONS,
    GMO_QUESTIONS,
    SAFETY_QUESTIONS,
    COMPOSITION_QUESTIONS,
    MICROBIOLOGICAL_QUESTIONS,
    REGULATORY_QUESTIONS
)

# Try to import PyMuPDF for PDF preview
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def create_analysis_prompt(document_content, questions, category):
    """Create a specialized prompt for document analysis"""
    return f"""You are a specialized document analysis assistant focused on {category} information extraction.

DOCUMENT CONTENT:
{document_content}

INSTRUCTIONS:
1. Answer each question based ONLY on the information explicitly stated in the provided document(s)
2. If the information is not available in the document, respond with "No data available to answer this question"
3. Do NOT make assumptions or provide general knowledge answers
4. For each answer, provide the source reference (document name/section where the information was found)
5. Be precise and extract exact values/information as stated in the document
6. For Yes/No questions, only answer Yes if explicitly confirmed in the document, otherwise answer No or Unknown

QUESTIONS TO ANALYZE:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions)])}

Please provide answers in the following format:
Question: [Question text]
Answer: [Your answer based on document content]
Source: [Document name/section where information was found]
---

If no relevant information is found for a question, use:
Question: [Question text]
Answer: No data available to answer this question
Source: Information not found in provided documents
---
"""

def process_analysis_questions(client, document_content, questions, category, model):
    """Process questions using RAG pipeline"""
    try:
        prompt = create_analysis_prompt(document_content, questions, category)
        
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise document analysis assistant. Extract information only from the provided documents."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error processing {category} analysis: {str(e)}"

def parse_analysis_results(analysis_text):
    """Parse the analysis results into structured format"""
    results = []
    sections = analysis_text.split("---")

    for section in sections:
        if section.strip():
            lines = section.strip().split("\n")
            question = ""
            answer = ""
            source = ""
            
            for line in lines:
                if line.startswith("Question:"):
                    question = line.replace("Question:", "").strip()
                elif line.startswith("Answer:"):
                    answer = line.replace("Answer:", "").strip()
                elif line.startswith("Source:"):
                    source = line.replace("Source:", "").strip()
            
            if question and answer:
                results.append({
                    "question": question,
                    "answer": answer,
                    "source": source
                })

    return results

def display_all_questions_with_results(questions, results, category_name):
    """Display all questions for a category, showing results if available"""
    st.markdown(f"### {category_name} Questions & Analysis")

    # Create a mapping of questions to results for exact matching
    result_map = {}
    if results:
        for result in results:
            # Try to match questions more flexibly
            question_key = result['question'].strip().lower()
            result_map[question_key] = result
    
    # Also create a mapping by question index for fallback
    result_by_index = {}
    if results:
        for i, result in enumerate(results):
            result_by_index[i] = result

    # Display all questions
    for i, question in enumerate(questions, 1):
        with st.expander(f"Q{i}: {question[:60]}..." if len(question) > 60 else f"Q{i}: {question}", expanded=False):
            st.markdown(f"**Question:** {question}")
            
            # Try multiple matching strategies
            result = None
            
            # Strategy 1: Exact question match
            question_key = question.strip().lower()
            if question_key in result_map:
                result = result_map[question_key]
            
            # Strategy 2: Try to find by partial match
            if not result:
                for res_question, res_data in result_map.items():
                    if question.lower() in res_question or res_question in question.lower():
                        result = res_data
                        break
            
            # Strategy 3: Use index-based matching as fallback
            if not result and (i-1) < len(result_by_index):
                result = result_by_index[i-1]
            
            # Display result or fallback message
            if result:
                answer = result['answer']
                
                # Color code the answer based on content
                if "No data available" in answer:
                    st.markdown(f"**Answer:** :red[{answer}]")
                elif any(word in answer.lower() for word in ['yes', 'present', 'contains', 'certified']):
                    st.markdown(f"**Answer:** :green[{answer}]")
                elif any(word in answer.lower() for word in ['no', 'free', 'not present', 'does not contain']):
                    st.markdown(f"**Answer:** :blue[{answer}]")
                else:
                    st.markdown(f"**Answer:** {answer}")
                
                st.markdown(f"**Source:** {result['source']}")
            else:
                # Show that analysis was not found for this specific question
                st.markdown("**Answer:** :orange[No specific analysis found for this question]")
                st.markdown("**Source:** :orange[Question not processed in current analysis]")

# Function to load and encode the logo
def get_logo_base64():
    # Path to your logo file - adjust this to where you save the logo
    logo_path = "Logo_Bayer.svg"

    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_data = f.read()
            encoded_logo = base64.b64encode(logo_data).decode()
            return encoded_logo
    return None

# Function to render PDF pages as images with scrollable view
def render_pdf_preview_scrollable(pdf_bytes, max_pages=10, page_width=600):
    """Render PDF pages as images for scrollable view."""
    if not PYMUPDF_AVAILABLE:
        return None, 0

    try:
        # Create a memory buffer from the PDF bytes
        memory_buffer = io.BytesIO(pdf_bytes)
        
        # Open the PDF from the memory buffer
        doc = fitz.open(stream=memory_buffer, filetype="pdf")
        
        total_pages = doc.page_count
        # Limit the number of pages to render for performance
        pages_to_render = min(total_pages, max_pages)
        
        images = []
        for page_num in range(pages_to_render):
            page = doc.load_page(page_num)
            
            # Calculate zoom factor based on desired width
            page_rect = page.rect
            zoom_factor = page_width / page_rect.width
            
            # Render page to an image with calculated zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
            img_data = pix.tobytes("png")
            images.append({
                'image': img_data,
                'page_num': page_num + 1,
                'width': pix.width,
                'height': pix.height
            })
        
        doc.close()
        return images, total_pages
    except Exception as e:
        st.error(f"Error rendering PDF preview: {e}")
        return None, 0

# Function to create download links
def create_download_link(data, filetype, filename):
    """Create a download link for data."""
    if isinstance(data, str):
        b64 = base64.b64encode(data.encode()).decode()
    else:
        b64 = base64.b64encode(data).decode()
    href = f'<a href="data:{filetype};base64,{b64}" download="{filename}" style="text-decoration: none; background-color: #4F8BF9; color: white; padding: 8px 16px; border-radius: 4px; margin: 2px;">📥 {filename}</a>'
    return href

def create_comprehensive_download_options(ocr_results, file_names):
    """Create download options for all OCR results combined"""
    if not ocr_results:
        return []

    # Create comprehensive text content
    comprehensive_text = "# Document Intelligence System - OCR Results\n\n"
    comprehensive_text += f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    comprehensive_text += f"Total Documents Processed: {len(ocr_results)}\n\n"
    comprehensive_text += "=" * 80 + "\n\n"

    for idx, (result, file_name) in enumerate(zip(ocr_results, file_names)):
        comprehensive_text += f"## Document {idx+1}: {file_name}\n\n"
        comprehensive_text += f"**File:** {file_name}\n"
        comprehensive_text += f"**Characters Extracted:** {len(result):,}\n\n"
        comprehensive_text += "### Extracted Content:\n\n"
        comprehensive_text += result
        comprehensive_text += "\n\n" + "=" * 80 + "\n\n"

    # Create JSON structure
    comprehensive_json = {
        "metadata": {
            "generated_on": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_documents": len(ocr_results),
            "total_characters": sum(len(result) for result in ocr_results)
        },
        "documents": []
    }

    for idx, (result, file_name) in enumerate(zip(ocr_results, file_names)):
        comprehensive_json["documents"].append({
            "document_id": idx + 1,
            "file_name": file_name,
            "character_count": len(result),
            "extracted_text": result
        })

    json_content = json.dumps(comprehensive_json, ensure_ascii=False, indent=2)

    # Create CSV content
    csv_content = "Document_ID,File_Name,Character_Count,Extracted_Text\n"
    for idx, (result, file_name) in enumerate(zip(ocr_results, file_names)):
        # Escape quotes and newlines for CSV
        escaped_text = result.replace('"', '""').replace('\n', '\\n').replace('\r', '\\r')
        csv_content += f'{idx+1},"{file_name}",{len(result)},"{escaped_text}"\n'

    # Create download links
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    download_links = [
        create_download_link(comprehensive_text, "text/plain", f"OCR_Results_Complete_{timestamp}.txt"),
        create_download_link(comprehensive_text, "text/markdown", f"OCR_Results_Complete_{timestamp}.md"),
        create_download_link(json_content, "application/json", f"OCR_Results_Complete_{timestamp}.json"),
        create_download_link(csv_content, "text/csv", f"OCR_Results_Complete_{timestamp}.csv")
    ]

    return download_links

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

def validate_and_convert_image(file_bytes, file_name, mime_type):
    """Validate image format and convert PNG to JPEG if needed"""
    try:
        from PIL import Image
        import io
        
        # Check if it's a PNG file
        if mime_type == "image/png" or file_name.lower().endswith('.png'):
            # Convert PNG to JPEG
            image = Image.open(io.BytesIO(file_bytes))
            
            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA'):
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save as JPEG
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=95)
            converted_bytes = output_buffer.getvalue()
            
            # Update filename and mime type
            new_filename = file_name.rsplit('.', 1)[0] + '_converted.jpg'
            new_mime_type = "image/jpeg"
            
            return converted_bytes, new_filename, new_mime_type, True
        
        # For supported formats, return as-is
        return file_bytes, file_name, mime_type, False
        
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

# Page configuration with improved styling
st.set_page_config(
    page_title="Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# COMPLETELY FIXED CSS - REMOVED ALL WHITE GAPS
st.markdown("""
<style>
/* Main styling */
.main-header {
    font-size: 2.8rem;
    color: #2563eb;
    margin-bottom: 1rem;
    font-weight: 700;
}
.sub-header {
    font-size: 1.5rem;
    color: #4F8BF9;
    margin-bottom: 0.5rem;
}

/* Button styling */
.stButton>button {
    background: linear-gradient(135deg, #4F8BF9, #3670CC);
    color: white;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(79, 139, 249, 0.2);
}
.stButton>button:hover {
    background: linear-gradient(135deg, #3670CC, #2563eb);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(79, 139, 249, 0.3);
}

/* Container styling */
.result-container {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9);
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    max-height: 600px;
    overflow-y: auto;
    overflow-x: auto;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.pdf-preview-container {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9);
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    max-height: 600px;
    overflow-y: auto;
    overflow-x: auto;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

/* Chat message styling */
.chat-message {
    padding: 1.2rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.chat-message.user {
    background: linear-gradient(135deg, #e6f3ff, #dbeafe);
    border-left: 4px solid #4F8BF9;
}
.chat-message.assistant {
    background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
    border-left: 4px solid #10b981;
}

/* Sidebar styling */
.sidebar-content {
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8fafc, #f1f5f9);
    border-radius: 12px;
    margin-bottom: 1rem;
}

/* Logo container */
.logo-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, #ffffff, #f8fafc);
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.logo-img {
    width: 150px;
    height: auto;
}

/* Status bars */
.pdf-info-bar {
    background: linear-gradient(135deg, #dbeafe, #bfdbfe);
    border: 1px solid #93c5fd;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    text-align: center;
    color: #1e40af;
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.15);
}

.page-number-badge {
    background: linear-gradient(135deg, #4F8BF9, #3670CC);
    color: white;
    padding: 10px 24px;
    border-radius: 30px;
    font-weight: bold;
    margin-bottom: 20px;
    display: inline-block;
    font-size: 1rem;
    box-shadow: 0 3px 6px rgba(79, 139, 249, 0.3);
    text-align: center;
}

/* FIXED: Results header - MINIMAL MARGINS */
.results-header {
    display: flex;
    align-items: center;
    margin: 0.5rem 0 0.25rem 0 !important;  /* Drastically reduced */
    font-size: 2rem;
    font-weight: 700;
    color: #1e293b;
    padding: 0.75rem !important;  /* Reduced padding */
    background: linear-gradient(135deg, #ffffff, #f8fafc);
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.results-icon {
    width: 32px;
    height: 32px;
    margin-right: 16px;
    background: linear-gradient(135deg, #4F8BF9, #3670CC);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 18px;
    box-shadow: 0 2px 4px rgba(79, 139, 249, 0.3);
}

/* FIXED: Enhanced Tab Styling - ZERO GAPS */
.custom-tabs-container {
    margin: 0 !important;  /* Removed all margins */
    padding: 0 !important;
    border-bottom: none;
    background: transparent;
}

/* Main tab buttons */
div[data-testid="column"] .stButton > button {
    border: none !important;
    background: linear-gradient(135deg, #f1f5f9, #e2e8f0) !important;
    color: #64748b !important;
    padding: 12px 20px !important;
    margin: 0 2px !important;  /* Minimal margin */
    border-radius: 12px 12px 0 0 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    position: relative !important;
    z-index: 1 !important;
    min-height: 45px !important;
}

/* Active Tab */
div[data-testid="column"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4F8BF9, #3670CC) !important;
    color: white !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(79, 139, 249, 0.4) !important;
    z-index: 2 !important;
    transform: translateY(-1px) !important;  /* Reduced transform */
}

/* Inactive Tab Hover */
div[data-testid="column"] .stButton > button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #e2e8f0, #cbd5e1) !important;
    color: #475569 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.1) !important;
}

/* FIXED: Tab content area - ZERO SPACING */
.tab-content {
    border-top: 4px solid #4F8BF9;
    padding: 0.5rem !important;  /* Minimal padding */
    margin-top: 0 !important;
    background: linear-gradient(135deg, #ffffff, #f8fafc);
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    min-height: 150px !important;  /* Reduced min-height */
}

/* FIXED: Analysis containers - ZERO GAPS */
.analysis-container {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9);
    border-radius: 16px;
    padding: 0.75rem !important;  /* Minimal padding */
    margin: 0.25rem 0 !important;  /* Minimal margin */
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.analysis-header {
    background: linear-gradient(135deg, #4F8BF9, #3670CC);
    color: white;
    padding: 0.75rem !important;  /* Minimal padding */
    border-radius: 12px;
    margin-bottom: 0.5rem !important;  /* Minimal margin */
    text-align: center;
    font-weight: bold;
    font-size: 1.1rem;
    box-shadow: 0 4px 8px rgba(79, 139, 249, 0.3);
}

/* FIXED: Remove ALL excessive margins and padding */
.main h3 {
    margin-top: 0.25rem !important;
    margin-bottom: 0.25rem !important;
}

.stMarkdown h3 {
    margin-top: 0.25rem !important;
    margin-bottom: 0.25rem !important;
}

/* FIXED: Remove Streamlit default spacing */
.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}

/* FIXED: Remove gaps between sections */
.element-container {
    margin-bottom: 0.25rem !important;
}

/* FIXED: Compact section spacing */
div[data-testid="stVerticalBlock"] > div {
    gap: 0.25rem !important;
}

/* Remove default Streamlit styling conflicts */
.stTabs [data-baseweb="tab-list"] {
    display: none !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding: 0 !important;
}

/* Enhanced expander styling */
.streamlit-expanderHeader {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9) !important;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}

/* Metric styling improvements */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #ffffff, #f8fafc);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* Responsive improvements */
@media (max-width: 768px) {
    .main-header {
        font-size: 2rem;
    }
    
    .logo-container {
        flex-direction: column;
        text-align: center;
    }
    
    .logo-img {
        width: 120px;
        margin-top: 1rem;
    }
    
    div[data-testid="column"] .stButton > button {
        padding: 8px 12px !important;
        font-size: 12px !important;
        margin: 0 1px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Display logo and app title
logo_base64 = get_logo_base64()
if logo_base64:
    st.markdown(
        f"""
        <div class="logo-container">
            <div>
                <h1 class='main-header'>Document Intelligence System</h1>
                <p style="font-size: 1.1rem; color: #64748b; margin: 0;">Extract, analyze, and query documents using advanced OCR and RAG capabilities</p>
            </div>
            <img src="data:image/svg+xml;base64,{logo_base64}" class="logo-img">
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown("<h1 class='main-header'>Document Intelligence System</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>Extract, analyze, and query documents using advanced OCR and RAG capabilities</p>", unsafe_allow_html=True)

# Initialize session state
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = []
if "preview_sources" not in st.session_state:
    st.session_state.preview_sources = []
if "file_names" not in st.session_state:
    st.session_state.file_names = []
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = []
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "document"
if "active_summary_tab" not in st.session_state:
    st.session_state.active_summary_tab = "overview"
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {}

# Enhanced Sidebar configuration
with st.sidebar:
    st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>⚙️ Configuration</h2>", unsafe_allow_html=True)

    # API key input
    api_key_input = st.text_input("🔑 Enter your Mistral API Key", type="password")
    api_key = clean_api_key(api_key_input)

    if not api_key:
        st.warning("⚠️ Please enter your API key to continue.")

    # Model selection for RAG
    rag_model = st.selectbox(
        "🤖 Select LLM for Question Answering",
        ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-7b"],
        index=0
    )

    # File type selection with supported formats
    file_type = st.radio("📄 Select file type", ("PDF", "Image"))

    # Source type selection
    source_type = st.radio("📂 Select source type", ("Local Upload", "URL"))

    # Add format information
    if file_type == "Image":
        st.info("📝 **Supported formats:** JPG, JPEG only. PNG files will be automatically converted to JPEG.")
    else:
        st.info("📝 **Supported formats:** PDF files")

    # Processing options
    st.markdown("### 🔧 Processing Options")
    max_pdf_pages = st.slider("Max PDF pages to render", 1, 20, 10, help="Higher values may slow down rendering")
    pdf_page_width = st.slider("PDF page width (pixels)", 400, 800, 600, help="Adjust PDF preview size")
    include_metadata = st.checkbox("Include metadata in results", value=True)

    # Analysis options
    st.markdown("### 📊 Analysis Options")
    auto_analyze = st.checkbox("Auto-analyze documents after processing", value=True, help="Automatically run structured analysis")

    st.markdown("</div>", unsafe_allow_html=True)

# Main content area
if not api_key:
    st.info("👈 Please enter your Mistral API key in the sidebar to get started.")
    st.stop()

# Enhanced Input section
st.markdown("## 📁 Document Input")

input_url = ""
uploaded_files = []

if source_type == "URL":
    input_url = st.text_area(
        "🌐 Enter one or multiple URLs (separate with new lines)",
        placeholder="https://example.com/document.pdf\nhttps://example.com/image.jpg",
        height=100
    )
else:
    # Only include supported formats for Mistral OCR
    if file_type == "PDF":
        file_types = ["pdf"]
        help_text = "Upload PDF files only"
    else:
        file_types = ["jpg", "jpeg"]  # Remove PNG as it's not supported
        help_text = "Upload JPG/JPEG images only (PNG not supported by OCR API)"

    uploaded_files = st.file_uploader(
        f"📤 Upload one or more {file_type.lower()} files",
        type=file_types,
        accept_multiple_files=True,
        help=help_text
    )

# Enhanced Process button
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    process_button = st.button("🚀 Process Documents", type="primary", use_container_width=True)

if process_button:
    if source_type == "URL" and not input_url.strip():
        st.error("Please enter at least one valid URL.")
    elif source_type == "Local Upload" and not uploaded_files:
        st.error("Please upload at least one file.")
    else:
        # Initialize Mistral client
        try:
            client = Mistral(api_key=api_key)
        except Exception as e:
            st.error(f"Error initializing Mistral client: {str(e)}")
            st.stop()
        
        # Clear previous results
        st.session_state.ocr_results = []
        st.session_state.preview_sources = []
        st.session_state.file_names = []
        st.session_state.pdf_bytes = []
        st.session_state.image_bytes = []
        st.session_state.chat_history = {}
        st.session_state.analysis_results = {}
        
        # Prepare sources
        sources = input_url.split("\n") if source_type == "URL" else uploaded_files
        sources = [s.strip() for s in sources if s.strip()] if source_type == "URL" else sources
        
        # Process each document with enhanced progress display
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, source in enumerate(sources):
            progress = (idx + 1) / len(sources)
            progress_bar.progress(progress)
            
            if source_type == "URL":
                source_name = source
                status_text.text(f"🔄 Processing URL {idx+1}/{len(sources)}: {source_name}")
            else:
                source_name = source.name
                status_text.text(f"🔄 Processing file {idx+1}/{len(sources)}: {source_name}")
            
            try:
                # Prepare document for processing
                if file_type == "PDF":
                    if source_type == "URL":
                        document = {"type": "document_url", "document_url": source}
                        preview_src = source
                        pdf_bytes = None
                    else:
                        file_bytes = source.read()
                        encoded_pdf = base64.b64encode(file_bytes).decode("utf-8")
                        document = {"type": "document_url", "document_url": f"data:application/pdf;base64,{encoded_pdf}"}
                        preview_src = f"data:application/pdf;base64,{encoded_pdf}"
                        pdf_bytes = file_bytes
                else:  # Image
                    if source_type == "URL":
                        # For URLs, we can't pre-validate, so we'll let the API handle it
                        document = {"type": "image_url", "image_url": source}
                        preview_src = source
                        image_bytes = None
                    else:
                        file_bytes = source.read()
                        original_mime_type = source.type
                        
                        # Validate and convert if necessary
                        try:
                            processed_bytes, processed_name, processed_mime_type, was_converted = validate_and_convert_image(
                                file_bytes, source.name, original_mime_type
                            )
                            
                            if was_converted:
                                st.info(f"ℹ️ Converted {source.name} from PNG to JPEG for OCR compatibility")
                            
                            encoded_image = base64.b64encode(processed_bytes).decode("utf-8")
                            document = {"type": "image_url", "image_url": f"data:{processed_mime_type};base64,{encoded_image}"}
                            preview_src = f"data:{processed_mime_type};base64,{encoded_image}"
                            image_bytes = processed_bytes
                            
                            # Update the stored filename if converted
                            if was_converted:
                                st.session_state.file_names[len(st.session_state.file_names)] = processed_name
                            
                        except Exception as e:
                            st.error(f"Error processing image {source.name}: {str(e)}")
                            continue
                
                # Process with Mistral OCR
                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True
                )
                
                # Add delay to prevent rate limiting
                time.sleep(1)
                
                # Extract results
                pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                result_text = "\n\n".join(page.markdown for page in pages) if pages else "No text extracted."
                
                # Store results
                st.session_state.ocr_results.append(result_text)
                st.session_state.preview_sources.append(preview_src)
                st.session_state.file_names.append(source_name if source_type == "URL" else source.name)
                
                if file_type == "PDF":
                    st.session_state.pdf_bytes.append(pdf_bytes)
                    st.session_state.image_bytes.append(None)
                else:
                    st.session_state.pdf_bytes.append(None)
                    st.session_state.image_bytes.append(image_bytes)
                
                # Initialize chat history for this document
                doc_id = str(uuid.uuid4())
                st.session_state.chat_history[doc_id] = []
                
            except Exception as e:
                st.error(f"Error processing {source_name}: {str(e)}")
                # Still add empty entries to maintain index consistency
                st.session_state.ocr_results.append(f"Error processing document: {str(e)}")
                st.session_state.preview_sources.append("")
                st.session_state.file_names.append(source_name if source_type == "URL" else source.name)
                st.session_state.pdf_bytes.append(None)
                st.session_state.image_bytes.append(None)
                doc_id = str(uuid.uuid4())
                st.session_state.chat_history[doc_id] = []
        
        progress_bar.progress(1.0)
        status_text.text("✅ Processing complete!")
        st.session_state.processing_complete = True
        
        # GUARANTEED AUTO-ANALYSIS - ALWAYS RUNS
        if auto_analyze and st.session_state.ocr_results:
            status_text.text("🔍 Running comprehensive analysis...")
            
            # Combine all document content for analysis
            combined_content = ""
            for idx, result in enumerate(st.session_state.ocr_results):
                file_name = st.session_state.file_names[idx]
                combined_content += f"\n\n=== DOCUMENT {idx+1}: {file_name} ===\n\n{result}\n\n"
            
            # Run analysis for each category - ENSURE ALL CATEGORIES ARE PROCESSED
            categories = {
                "nutrient": NUTRIENT_QUESTIONS,
                "dietary": DIETARY_QUESTIONS,
                "allergen": ALLERGEN_QUESTIONS,
                "gmo": GMO_QUESTIONS,
                "safety": SAFETY_QUESTIONS,
                "composition": COMPOSITION_QUESTIONS,
                "microbiological": MICROBIOLOGICAL_QUESTIONS,
                "regulatory": REGULATORY_QUESTIONS
            }
            
            for category, questions in categories.items():
                try:
                    status_text.text(f"🔍 Analyzing {category.title()} information...")
                    analysis_result = process_analysis_questions(
                        client, combined_content, questions, category, rag_model
                    )
                    parsed_results = parse_analysis_results(analysis_result)
                    
                    # ENSURE results are stored properly
                    if parsed_results:
                        st.session_state.analysis_results[category] = parsed_results
                        st.success(f"✅ {category.title()} analysis completed! ({len(parsed_results)} results)")
                    else:
                        st.warning(f"⚠️ {category.title()} analysis returned no results")
                        st.session_state.analysis_results[category] = []
                    
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    st.session_state.analysis_results[category] = []
                    st.error(f"Error analyzing {category}: {str(e)}")
            
            status_text.text("✅ Complete analysis finished!")
            
            # Debug: Show analysis results count
            total_results = sum(len(results) for results in st.session_state.analysis_results.values())
            st.info(f"📊 Analysis complete! Total results: {total_results}")
        
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

# Display results if available
if st.session_state.ocr_results:
    # FIXED: Results Header with MINIMAL spacing
    st.markdown("""
    <div class="results-header">
        <div class="results-icon">📊</div>
        Results
    </div>
    """, unsafe_allow_html=True)

    # FIXED: Tab Navigation with ZERO gaps
    st.markdown('<div class="custom-tabs-container">', unsafe_allow_html=True)

    # Create three columns for the main tab buttons
    col1, col2, col3, col_spacer = st.columns([1, 1, 1, 3])

    with col1:
        # Document View Tab
        doc_button_type = "primary" if st.session_state.active_tab == "document" else "secondary"
        if st.button("📄 Document View", 
                    key="tab_document",
                    use_container_width=True,
                    type=doc_button_type):
            st.session_state.active_tab = "document"
            st.rerun()

    with col2:
        # Question Answering Tab
        qa_button_type = "primary" if st.session_state.active_tab == "qa" else "secondary"
        if st.button("💬 Question Answering", 
                    key="tab_qa",
                    use_container_width=True,
                    type=qa_button_type):
            st.session_state.active_tab = "qa"
            st.rerun()

    with col3:
        # Summary Tab
        summary_button_type = "primary" if st.session_state.active_tab == "summary" else "secondary"
        if st.button("📈 Summary", 
                    key="tab_summary",
                    use_container_width=True,
                    type=summary_button_type):
            st.session_state.active_tab = "summary"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # FIXED: Tab Content with ZERO spacing
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)

    if st.session_state.active_tab == "document":
        st.markdown("### 📄 Document Processing Results")
        
        # Display each document
        for idx, result in enumerate(st.session_state.ocr_results):
            with st.expander(f"📄 Document {idx+1}: {st.session_state.file_names[idx]}", expanded=idx==0):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("#### 🖼️ Document Preview")
                    
                    if file_type == "PDF":
                        # Handle PDF preview with scrollable container
                        pdf_bytes = st.session_state.pdf_bytes[idx]
                        if pdf_bytes:
                            # Download button
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_bytes,
                                file_name=st.session_state.file_names[idx],
                                mime="application/pdf",
                                key=f"download_pdf_{idx}"
                            )
                            
                            # Render PDF preview using native Streamlit components
                            if PYMUPDF_AVAILABLE:
                                with st.spinner("Rendering PDF preview..."):
                                    page_images, total_pages = render_pdf_preview_scrollable(
                                        pdf_bytes, 
                                        max_pdf_pages, 
                                        pdf_page_width
                                    )
                                    
                                    if page_images:
                                        # PDF info bar
                                        pages_shown = len(page_images)
                                        st.markdown(
                                            f"""
                                            <div class='pdf-info-bar'>
                                                📄 Showing {pages_shown} of {total_pages} pages
                                                {f" (Limited to {max_pdf_pages} pages for performance)" if total_pages > max_pdf_pages else ""}
                                            </div>
                                            """,
                                            unsafe_allow_html=True
                                        )
                                        
                                        # Create a scrollable container using HTML with enhanced styling
                                        pdf_content = ""
                                        for page_data in page_images:
                                            # Convert image to base64 for HTML display
                                            img_b64 = base64.b64encode(page_data['image']).decode()
                                            
                                            pdf_content += f"""
                                            <div style="margin-bottom: 30px; text-align: center;">
                                                <div class="page-number-badge">Page {page_data['page_num']}</div>
                                                <div style="text-align: center;">
                                                    <img src="data:image/png;base64,{img_b64}" 
                                                         style="max-width: 100%; height: auto; border: 2px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                                                </div>
                                            </div>
                                            """
                                            
                                            # Add separator between pages (except for the last page)
                                            if page_data['page_num'] < len(page_images):
                                                pdf_content += "<div style='border-top: 2px solid #e2e8f0; margin: 25px 0; padding-top: 20px;'></div>"
                                        
                                        # Display the scrollable PDF container
                                        st.markdown(f"<div class='pdf-preview-container'>{pdf_content}</div>", unsafe_allow_html=True)
                                        
                                        # Additional controls
                                        if total_pages > max_pdf_pages:
                                            st.info(f"💡 Tip: Increase 'Max PDF pages to render' in the sidebar to view more pages (currently showing {pages_shown}/{total_pages})")
                                    else:
                                        st.warning("Could not render PDF preview.")
                            else:
                                st.info("Install PyMuPDF for PDF preview: `pip install pymupdf`")
                                st.warning("PDF preview is not available. Please download the file to view it.")
                        else:
                            # URL-based PDF
                            preview_src = st.session_state.preview_sources[idx]
                            if preview_src:
                                st.markdown(f"[📎 Open PDF]({preview_src})")
                                st.info("PDF preview is not available for URL-based documents. Click the link above to view.")
                    else:
                        # Handle image preview
                        if source_type == "Local Upload" and st.session_state.image_bytes[idx]:
                            st.image(st.session_state.image_bytes[idx], use_column_width=True)
                        else:
                            st.image(st.session_state.preview_sources[idx], use_column_width=True)
                
                with col2:
                    st.markdown("#### 📝 OCR Results")
                    
                    # Display OCR results in a scrollable container
                    st.markdown(f"<div class='result-container'>{result}</div>", unsafe_allow_html=True)
                    
                    # Download options
                    st.markdown("#### 📥 Download Options")
                    
                    file_name_base = os.path.splitext(st.session_state.file_names[idx])[0]
                    
                    # Create download links
                    json_data = json.dumps({"ocr_result": result}, ensure_ascii=False, indent=2)
                    
                    download_links = [
                        create_download_link(result, "text/plain", f"{file_name_base}_ocr.txt"),
                        create_download_link(result, "text/markdown", f"{file_name_base}_ocr.md"),
                        create_download_link(json_data, "application/json", f"{file_name_base}_ocr.json")
                    ]
                    
                    for link in download_links:
                        st.markdown(link, unsafe_allow_html=True)
        
        # Add comprehensive download section after individual documents
        st.markdown("---")
        st.markdown("### 📥 Download Complete OCR Results")
        st.markdown("Download all extracted text from all processed documents in various formats:")
        
        # Create comprehensive download options
        comprehensive_downloads = create_comprehensive_download_options(
            st.session_state.ocr_results, 
            st.session_state.file_names
        )
        
        # Display download options in columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📄 Text Formats:**")
            if len(comprehensive_downloads) >= 2:
                st.markdown(comprehensive_downloads[0], unsafe_allow_html=True)  # TXT
                st.markdown(comprehensive_downloads[1], unsafe_allow_html=True)  # MD
        
        with col2:
            st.markdown("**📊 Data Formats:**")
            if len(comprehensive_downloads) >= 4:
                st.markdown(comprehensive_downloads[2], unsafe_allow_html=True)  # JSON
                st.markdown(comprehensive_downloads[3], unsafe_allow_html=True)  # CSV
        
        # Summary info
        total_chars = sum(len(result) for result in st.session_state.ocr_results)
        st.info(f"📊 **Summary:** {len(st.session_state.ocr_results)} documents • {total_chars:,} total characters extracted")

    elif st.session_state.active_tab == "qa":
        st.markdown("### 💬 Question Answering")

        # Document selection with "All Documents" option
        if len(st.session_state.ocr_results) > 1:
            # Create options list with "All Documents" as first option
            doc_options = ["📚 All Documents"] + [f"📄 Document {i+1}: {st.session_state.file_names[i]}" for i in range(len(st.session_state.file_names))]
        
            selected_option = st.selectbox(
                "📂 Select document to query:",
                range(len(doc_options)),
                format_func=lambda i: doc_options[i],
                key="doc_selector_qa"
            )
        
            # Determine if "All Documents" is selected
            is_all_documents = (selected_option == 0)
            selected_doc = selected_option - 1 if not is_all_documents else None
        
            # Display info about selection
            if is_all_documents:
                st.info(f"📚 Querying across all {len(st.session_state.ocr_results)} documents")
            else:
                st.info(f"📄 Querying: {st.session_state.file_names[selected_doc]}")
        else:
            selected_doc = 0
            is_all_documents = False
            st.info(f"📄 Querying: {st.session_state.file_names[0]}")

        # Get document ID for chat history
        doc_ids = list(st.session_state.chat_history.keys())

        # Use special key for "All Documents" chat history
        if is_all_documents:
            chat_key = "all_documents"
            if chat_key not in st.session_state.chat_history:
                st.session_state.chat_history[chat_key] = []
            doc_id = chat_key
        else:
            if selected_doc < len(doc_ids):
                doc_id = doc_ids[selected_doc]
            else:
                doc_id = None

        if doc_id:
            # Display chat history
            if st.session_state.chat_history[doc_id]:
                st.markdown("#### 💬 Chat History")
                for message in st.session_state.chat_history[doc_id]:
                    role = message["role"]
                    content = message["content"]
                
                    st.markdown(f"<div class='chat-message {role}'>", unsafe_allow_html=True)
                    st.markdown(f"<div><strong>{'🧑‍💼 ' + role.capitalize()}</strong></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='content'>{content}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            # Question input with clearing functionality
            placeholder_text = "Ask a question about all documents..." if is_all_documents else "What is this document about?"

            # Use a flag to indicate when to clear the input
            clear_input_flag = f"clear_input_{doc_id}"
            if clear_input_flag not in st.session_state:
                st.session_state[clear_input_flag] = False

            # If we need to clear the input, reset the flag and use empty string
            if st.session_state[clear_input_flag]:
                input_value = ""
                st.session_state[clear_input_flag] = False
            else:
                # Use the current session state value or empty string
                input_key = f"question_input_{doc_id}"
                input_value = st.session_state.get(input_key, "")

            user_question = st.text_input(
                "❓ Ask a question about the document(s):",
                placeholder=placeholder_text,
                value=input_value,
                key=f"question_input_{doc_id}"
            )

            col1, col2 = st.columns([1, 4])
            with col1:
                submit_question = st.button(
                    "🚀 Submit Question", 
                    key=f"submit_{doc_id}",
                    help="Click to submit your question",
                    use_container_width=True
                )
            with col2:
                clear_history = st.button(
                    "🗑️ Clear History", 
                    key=f"clear_{doc_id}",
                    help="Click to clear chat history",
                    use_container_width=True
                )

            if submit_question and user_question.strip():
                # Show visual feedback for button click
                with st.spinner("🤔 Processing your question..."):
                    # Add user question to chat history
                    st.session_state.chat_history[doc_id].append({
                        "role": "user",
                        "content": user_question
                    })

                    # Get document content based on selection
                    if is_all_documents:
                        # Combine all documents with clear separation
                        combined_content = ""
                        for idx, result in enumerate(st.session_state.ocr_results):
                            file_name = st.session_state.file_names[idx]
                            combined_content += f"\n\n=== DOCUMENT {idx+1}: {file_name} ===\n\n{result}\n\n"

                        document_content = combined_content
                        context_info = f"all {len(st.session_state.ocr_results)} documents"
                    else:
                        document_content = st.session_state.ocr_results[selected_doc]
                        context_info = f"the document '{st.session_state.file_names[selected_doc]}'"

                    # Create system prompt
                    system_prompt = f"""You are a helpful assistant that answers questions based on the provided document(s).

Document content:
{document_content}

Answer questions based ONLY on the information in the document(s). When referencing information, please mention which document it comes from when applicable (e.g., "According to Document 1: filename.pdf" or "Based on the information in Document 2"). If the answer is not in the document(s), say "I don't have enough information to answer that question based on the document content." Be concise and accurate.

You are currently analyzing {context_info}."""

                    # Create messages for chat completion
                    messages = [{"role": "system", "content": system_prompt}]

                    # Add chat history
                    for msg in st.session_state.chat_history[doc_id]:
                        messages.append({"role": msg["role"], "content": msg["content"]})

                    # Get response from Mistral
                    try:
                        client = Mistral(api_key=api_key)
                        chat_response = client.chat.complete(
                            model=rag_model,
                            messages=messages
                        )

                        assistant_response = chat_response.choices[0].message.content

                        # Add assistant response to chat history
                        st.session_state.chat_history[doc_id].append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                    
                        # Set flag to clear input on next run
                        st.session_state[clear_input_flag] = True

                        # Show success message briefly
                        st.success("✅ Question processed successfully!")
                        time.sleep(0.5)

                        st.rerun()

                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")

            elif submit_question and not user_question.strip():
                st.warning("Please enter a question before submitting.")

            if clear_history:
                # Show visual feedback for button click
                with st.spinner("🗑️ Clearing chat history..."):
                    st.session_state.chat_history[doc_id] = []
                    # Set flag to clear input on next run
                    st.session_state[clear_input_flag] = True
                    
                    # Show success message briefly
                    st.success("🗑️ Chat history cleared!")
                    time.sleep(0.5)
                    
                    st.rerun()
        

    elif st.session_state.active_tab == "summary":
        # FIXED: Summary section with ZERO gaps
        st.markdown("### 📈 Summary & Analysis")
        
        # FIXED: Summary sub-tabs with ZERO spacing
        st.markdown('<div class="custom-tabs-container">', unsafe_allow_html=True)
        
        # First row of category tabs
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            overview_button_type = "primary" if st.session_state.active_summary_tab == "overview" else "secondary"
            if st.button("📊 Overview", 
                        key="summary_tab_overview",
                        use_container_width=True,
                        type=overview_button_type):
                st.session_state.active_summary_tab = "overview"
                st.rerun()
        
        with col2:
            nutrient_button_type = "primary" if st.session_state.active_summary_tab == "nutrient" else "secondary"
            if st.button("🥗 Nutrient", 
                        key="summary_tab_nutrient",
                        use_container_width=True,
                        type=nutrient_button_type):
                st.session_state.active_summary_tab = "nutrient"
                st.rerun()
        
        with col3:
            dietary_button_type = "primary" if st.session_state.active_summary_tab == "dietary" else "secondary"
            if st.button("🌱 Dietary", 
                        key="summary_tab_dietary",
                        use_container_width=True,
                        type=dietary_button_type):
                st.session_state.active_summary_tab = "dietary"
                st.rerun()
        
        with col4:
            allergen_button_type = "primary" if st.session_state.active_summary_tab == "allergen" else "secondary"
            if st.button("⚠️ Allergen", 
                        key="summary_tab_allergen",
                        use_container_width=True,
                        type=allergen_button_type):
                st.session_state.active_summary_tab = "allergen"
                st.rerun()
        
        with col5:
            gmo_button_type = "primary" if st.session_state.active_summary_tab == "gmo" else "secondary"
            if st.button("🧬 GMO", 
                        key="summary_tab_gmo",
                        use_container_width=True,
                        type=gmo_button_type):
                st.session_state.active_summary_tab = "gmo"
                st.rerun()
        
        # Second row of category tabs
        col1, col2, col3, col_spacer = st.columns([1, 1, 1, 2])
        
        with col1:
            safety_button_type = "primary" if st.session_state.active_summary_tab == "safety" else "secondary"
            if st.button("🛡️ Safety", 
                        key="summary_tab_safety",
                        use_container_width=True,
                        type=safety_button_type):
                st.session_state.active_summary_tab = "safety"
                st.rerun()
        
        with col2:
            composition_button_type = "primary" if st.session_state.active_summary_tab == "composition" else "secondary"
            if st.button("🧪 Composition", 
                        key="summary_tab_composition",
                        use_container_width=True,
                        type=composition_button_type):
                st.session_state.active_summary_tab = "composition"
                st.rerun()
        
        with col3:
            micro_button_type = "primary" if st.session_state.active_summary_tab == "microbiological" else "secondary"
            if st.button("🦠 Microbiological", 
                        key="summary_tab_microbiological",
                        use_container_width=True,
                        type=micro_button_type):
                st.session_state.active_summary_tab = "microbiological"
                st.rerun()
        
        # Third row for regulatory
        col1, col_spacer = st.columns([1, 4])
        
        with col1:
            regulatory_button_type = "primary" if st.session_state.active_summary_tab == "regulatory" else "secondary"
            if st.button("📋 Regulatory", 
                        key="summary_tab_regulatory",
                        use_container_width=True,
                        type=regulatory_button_type):
                st.session_state.active_summary_tab = "regulatory"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # FIXED: Summary tab content with ZERO spacing
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)
        
        if st.session_state.active_summary_tab == "overview":
            # Enhanced Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📄 Documents Processed", len(st.session_state.ocr_results))
            
            with col2:
                total_chars = sum(len(result) for result in st.session_state.ocr_results)
                st.metric("📝 Total Characters", f"{total_chars:,}")
            
            with col3:
                avg_chars = total_chars // len(st.session_state.ocr_results) if st.session_state.ocr_results else 0
                st.metric("📊 Avg Characters/Doc", f"{avg_chars:,}")
            
            with col4:
                total_questions = sum(len(history) // 2 for history in st.session_state.chat_history.values())
                st.metric("❓ Questions Asked", total_questions)
            
            # Document list
            st.markdown("#### 📋 Document Details")
            for idx, file_name in enumerate(st.session_state.file_names):
                char_count = len(st.session_state.ocr_results[idx])
                st.markdown(f"**{idx+1}. {file_name}** - {char_count:,} characters extracted")
            
            # Analysis status
            st.markdown("#### 📊 Analysis Status")
            if st.session_state.analysis_results:
                analysis_status = []
                categories = ["nutrient", "dietary", "allergen", "gmo", "safety", "composition", "microbiological", "regulatory"]
                for category in categories:
                    if category in st.session_state.analysis_results:
                        count = len(st.session_state.analysis_results[category])
                        analysis_status.append(f"✅ {category.title()}: {count} questions analyzed")
                    else:
                        analysis_status.append(f"❌ {category.title()}: Not analyzed")
                
                for status in analysis_status:
                    st.markdown(status)
            else:
                st.info("No structured analysis performed yet. Enable 'Auto-analyze' in sidebar or run manual analysis.")
        
            # Add comprehensive download section in overview
            st.markdown("---")
            st.markdown("#### 📥 Download Complete Results")
            
            # Create comprehensive download options
            comprehensive_downloads = create_comprehensive_download_options(
                st.session_state.ocr_results, 
                st.session_state.file_names
            )
            
            # Display download options in a more compact format for overview
            st.markdown("**Download all OCR results:**")
            download_cols = st.columns(4)
            
            format_names = ["📄 TXT", "📝 Markdown", "🔧 JSON", "📊 CSV"]
            for i, (col, download_link, format_name) in enumerate(zip(download_cols, comprehensive_downloads, format_names)):
                with col:
                    st.markdown(f"**{format_name}**")
                    st.markdown(download_link, unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "nutrient":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🥗 Nutrient Composition Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("nutrient", [])
            display_all_questions_with_results(NUTRIENT_QUESTIONS, results, "Nutrient Composition")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "dietary":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🌱 Dietary Information Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("dietary", [])
            display_all_questions_with_results(DIETARY_QUESTIONS, results, "Dietary Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "allergen":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">⚠️ Allergen Information Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("allergen", [])
            display_all_questions_with_results(ALLERGEN_QUESTIONS, results, "Allergen Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "gmo":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🧬 GMO Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("gmo", [])
            display_all_questions_with_results(GMO_QUESTIONS, results, "GMO Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "safety":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🛡️ Safety Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("safety", [])
            display_all_questions_with_results(SAFETY_QUESTIONS, results, "Safety Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "composition":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🧪 Composition Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("composition", [])
            display_all_questions_with_results(COMPOSITION_QUESTIONS, results, "Composition Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "microbiological":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">🦠 Microbiological Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("microbiological", [])
            display_all_questions_with_results(MICROBIOLOGICAL_QUESTIONS, results, "Microbiological Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.active_summary_tab == "regulatory":
            st.markdown('<div class="analysis-container">', unsafe_allow_html=True)
            st.markdown('<div class="analysis-header">📋 Regulatory Analysis</div>', unsafe_allow_html=True)
            
            results = st.session_state.analysis_results.get("regulatory", [])
            display_all_questions_with_results(REGULATORY_QUESTIONS, results, "Regulatory Information")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# Enhanced Footer
st.markdown("---")
logo_base64 = get_logo_base64()
if logo_base64:
    st.markdown(
        f"""
        <footer style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 30px; border-radius: 16px; margin-top: 40px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <img src="data:image/svg+xml;base64,{logo_base64}" style="width: 100px; height: auto; margin-bottom: 20px;">
            <p style="margin: 0; color: #1e293b; font-weight: bold; font-size: 1.1rem;">Document Intelligence System</p>
            <p style="margin: 5px 0; font-size: 0.9rem; color: #64748b;">Powered by Advanced OCR and RAG capabilities</p>
            <p style="margin: 0; font-size: 0.8rem; color: #94a3b8;">© 2024 Bayer. All rights reserved.</p>
        </footer>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown("<p style='text-align: center; color: #64748b;'>Document Intelligence System with OCR and RAG capabilities</p>", unsafe_allow_html=True)
