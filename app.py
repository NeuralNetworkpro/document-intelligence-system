import streamlit as st
import base64
import tempfile
import os
import json
import io
import uuid
import re
import time
import pandas as pd
from mistralai import Mistral
from PIL import Image
import numpy as np
from datetime import datetime

# Import enhanced tabular functionality
from tabular import (
    extract_all_tables_from_document,
    create_comprehensive_document_analysis,
    create_professional_excel_export,
    EXCEL_AVAILABLE
)

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

# Import the new comparison functionality
from comparison import render_comparison_tab

# Try to import PyMuPDF for PDF preview
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def estimate_tokens(text):
    """Estimate the number of tokens in a text (rough approximation)"""
    return len(text) / 4  # Rough estimate: ~4 characters per token

def extract_relevant_sections(document_content, category, max_tokens=6000):
    """Extract sections relevant to a specific category from document content"""
    
    # Category-specific keywords for better content filtering
    category_keywords = {
        "nutrient": [
            "nutrient", "nutrition", "nutritional", "energy", "protein", "fat", "carbohydrate", 
            "vitamin", "mineral", "kcal", "calorie", "sugar", "fiber", "fibre", "sodium", 
            "calcium", "iron", "potassium", "saturated", "unsaturated", "trans", "cholesterol",
            "ash", "moisture", "starch", "dietary fiber", "total fat", "monounsaturated",
            "polyunsaturated", "vitamin a", "vitamin c", "vitamin d", "vitamin e", "thiamin",
            "riboflavin", "niacin", "folate", "cobalamin", "mg/100g", "g/100g", "kj/100g",
            "per 100g", "per serving", "nutritional value", "nutritional information"
        ],
        "dietary": [
            "dietary", "halal", "kosher", "vegan", "vegetarian", "gluten", "lactose", 
            "organic", "natural", "free range", "grass fed", "non-dairy", "plant-based",
            "gluten-free", "lactose-free", "dairy-free", "egg-free", "nut-free", "soy-free",
            "certified", "certification", "religious", "diet", "dietary restriction"
        ],
        "allergen": [
            "allergen", "allergy", "allergic", "contain", "contains", "may contain", "trace", 
            "peanut", "nut", "tree nut", "milk", "dairy", "egg", "soy", "soya", "wheat", 
            "gluten", "fish", "shellfish", "crustacean", "mollusc", "celery", "mustard", 
            "sesame", "lupin", "sulphite", "sulfite", "cross-contamination", "allergen information",
            "allergy advice", "free from", "does not contain"
        ],
        "gmo": [
            "gmo", "genetic", "genetically", "modified", "organism", "dna", "gene", "transgenic", 
            "bioengineered", "biotechnology", "recombinant", "engineered", "modification",
            "non-gmo", "gmo-free", "genetically modified organism", "genetic engineering"
        ],
        "safety": [
            "safety", "heavy metal", "metals", "contaminant", "contamination", "residue", 
            "pesticide", "herbicide", "toxin", "toxic", "pathogen", "irradiation", "radiation",
            "lead", "mercury", "cadmium", "arsenic", "aflatoxin", "mycotoxin", "chemical",
            "hazard", "risk", "limit", "maximum", "acceptable", "safe", "unsafe"
        ],
        "composition": [
            "composition", "ingredient", "ingredients", "formulation", "component", "components",
            "carrier", "additive", "additives", "preservative", "preservatives", "percentage", 
            "percent", "%", "formula", "recipe", "constituent", "material", "substance",
            "compound", "mixture", "blend", "preparation"
        ],
        "microbiological": [
            "microbiological", "microbial", "microbe", "bacteria", "bacterial", "yeast", 
            "mold", "mould", "fungi", "pathogen", "pathogenic", "shelf life", "storage", 
            "temperature", "refrigeration", "freezing", "sterilization", "pasteurization",
            "cfu", "colony", "count", "salmonella", "listeria", "e.coli", "staphylococcus",
            "clostridium", "bacillus", "spoilage", "preservation"
        ],
        "regulatory": [
            "regulatory", "regulation", "regulations", "compliance", "compliant", "standard", 
            "standards", "requirement", "requirements", "certification", "certified", "approved", 
            "approval", "eu", "european", "fda", "usda", "bpom", "codex", "iso", "haccp",
            "brc", "ifs", "fssc", "legal", "law", "directive", "legislation", "authorized",
            "permitted", "prohibited", "banned", "restricted"
        ]
    }
    
    # Get keywords for the specific category
    keywords = category_keywords.get(category, [])
    
    # Split document into manageable chunks
    chunks = document_content.split("\n\n=== DOCUMENT")
    header = chunks[0] if chunks else ""
    documents = ["=== DOCUMENT" + chunk for chunk in chunks[1:]] if len(chunks) > 1 else [document_content]
    
    relevant_sections = []
    
    # Always include header information (contains metadata)
    if header.strip():
        relevant_sections.append(header)
    
    # Process each document
    for doc in documents:
        doc_lines = doc.split('\n')
        doc_header = doc_lines[0] if doc_lines else ""
        
        # Calculate keyword density for this document
        keyword_matches = 0
        for keyword in keywords:
            keyword_matches += doc.lower().count(keyword.lower())
        
        # If document has relevant keywords, include it
        if keyword_matches > 0:
            relevant_sections.append(doc)
        else:
            # Even if no direct keywords, include document header for context
            relevant_sections.append(f"{doc_header}\n\n[Document analyzed but no explicit {category} keywords found]")
    
    # Combine relevant sections
    combined_content = "\n\n".join(relevant_sections)
    
    # If still too large, prioritize sections with highest keyword density
    if estimate_tokens(combined_content) > max_tokens:
        # Score each section by keyword density
        section_scores = []
        for section in relevant_sections:
            keyword_count = sum(section.lower().count(keyword.lower()) for keyword in keywords)
            section_length = len(section)
            # Calculate density (keywords per 1000 characters)
            density = (keyword_count * 1000) / section_length if section_length > 0 else 0
            section_scores.append((section, keyword_count, density))
        
        # Sort by keyword count first, then by density
        section_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        # Take top sections until we're under the token limit
        prioritized_sections = []
        current_tokens = 0
        
        for section, count, density in section_scores:
            section_tokens = estimate_tokens(section)
            if current_tokens + section_tokens <= max_tokens:
                prioritized_sections.append(section)
                current_tokens += section_tokens
            else:
                # If we can't fit the whole section, try to fit part of it
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # Only if we have meaningful space left
                    chars_to_include = int(remaining_tokens * 4)  # Convert tokens back to chars
                    partial_section = section[:chars_to_include] + "\n[... content truncated ...]"
                    prioritized_sections.append(partial_section)
                break
        
        combined_content = "\n\n".join(prioritized_sections)
    
    return combined_content

def create_analysis_prompt(document_content, questions, category):
    """Create a specialized prompt for document analysis with enhanced instructions"""
    
    category_guidance = {
        "nutrient": "Look for nutritional tables, energy values, protein content, fat content, carbohydrates, vitamins, minerals, and any numerical nutritional data. Pay special attention to tables with columns like 'Nutrient', 'Value', 'Unit' or similar structures.",
        "dietary": "Look for dietary certifications, religious compliance (Halal, Kosher), dietary restrictions (Vegan, Vegetarian), and special dietary claims (Gluten-free, Organic, etc.).",
        "allergen": "Look for allergen declarations, 'contains' statements, 'may contain' warnings, and any mention of the 14 major allergens or cross-contamination risks.",
        "gmo": "Look for GMO status, genetic modification information, bioengineering details, and any statements about genetically modified organisms.",
        "safety": "Look for safety data, contaminant levels, heavy metals, pesticide residues, toxicological information, and safety limits.",
        "composition": "Look for ingredient lists, formulation details, component percentages, and compositional information.",
        "microbiological": "Look for microbial specifications, shelf life data, storage conditions, pathogen testing, and microbiological safety information.",
        "regulatory": "Look for regulatory compliance statements, certifications, standards compliance, and legal requirements."
    }
    
    specific_guidance = category_guidance.get(category, f"Look for information related to {category}")
    
    return f"""You are a specialized document analysis assistant focused on {category} information extraction.

DOCUMENT CONTENT:
{document_content}

CATEGORY-SPECIFIC GUIDANCE:
{specific_guidance}

INSTRUCTIONS:
1. Answer each question based ONLY on the information explicitly stated in the provided document(s)
2. If the information is not available in the document, respond with "No data available to answer this question"
3. Do NOT make assumptions or provide general knowledge answers
4. For each answer, provide the source reference (document name/section where the information was found)
5. Be precise and extract exact values/information as stated in the document
6. For Yes/No questions, only answer Yes if explicitly confirmed in the document, otherwise answer No or Unknown
7. IMPORTANT: Look for both direct and indirect information that could answer the questions
8. Be thorough - even if information is presented in tables, charts, or scattered across the document
9. For {category} questions specifically, look for related terms and synonyms
10. Pay special attention to numerical data, tables, and structured information
11. If you find partial information that relates to a question, include it in your answer

QUESTIONS TO ANALYZE:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions)])}

Please provide answers in the following format:
Question: [Question text]
Answer: [Your answer based on document content - be specific and include exact values when available]
Source: [Document name/section where information was found]
---

If no relevant information is found for a question, use:
Question: [Question text]
Answer: No data available to answer this question
Source: Information not found in provided documents
---

IMPORTANT: Be thorough and look carefully through all the provided content. Even if information seems scattered or is in table format, extract and compile it to answer the questions.
"""

def process_analysis_questions(client, document_content, questions, category, model):
    """Process questions using RAG pipeline with improved handling of large documents"""
    try:
        # Extract relevant sections for this category
        focused_content = extract_relevant_sections(document_content, category, max_tokens=6000)
        
        # Create enhanced prompt with category-specific guidance
        enhanced_prompt = create_analysis_prompt(focused_content, questions, category)
        
        # Use appropriate temperature for thorough exploration
        response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a precise document analysis assistant specializing in {category} information extraction. Extract information only from the provided documents. Be thorough and look for both direct and indirect information. Pay special attention to tables, numerical data, and structured information."
                },
                {"role": "user", "content": enhanced_prompt}
            ],
            temperature=0.7,  # Slightly higher temperature for more exploration
            max_tokens=2000   # Ensure we have enough tokens for comprehensive answers
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error processing {category} analysis: {str(e)}"

def prioritize_categories(document_content, categories):
    """Prioritize categories based on document content relevance"""
    
    category_keywords = {
        "nutrient": [
            "nutrient", "nutrition", "energy", "protein", "fat", "carbohydrate", 
            "vitamin", "mineral", "kcal", "calorie", "sugar", "fiber", "sodium"
        ],
        "dietary": [
            "dietary", "halal", "kosher", "vegan", "vegetarian", "gluten", 
            "lactose", "organic", "natural"
        ],
        "allergen": [
            "allergen", "allergy", "contain", "may contain", "trace", "peanut", 
            "nut", "milk", "egg", "soy", "wheat", "fish", "shellfish"
        ],
        "gmo": [
            "gmo", "genetic", "modified", "organism", "dna", "gene", "transgenic", 
            "bioengineered", "biotechnology"
        ],
        "safety": [
            "safety", "heavy metal", "contaminant", "residue", "pesticide", 
            "toxin", "pathogen", "irradiation", "radiation"
        ],
        "composition": [
            "composition", "ingredient", "formulation", "component", 
            "carrier", "additive", "preservative", "percentage"
        ],
        "microbiological": [
            "microbiological", "microbial", "bacteria", "yeast", "mold", 
            "pathogen", "shelf life", "storage", "temperature"
        ],
        "regulatory": [
            "regulatory", "regulation", "compliance", "standard", "requirement", 
            "certification", "approved", "eu", "fda", "usda", "bpom"
        ]
    }
    
    # Score each category based on keyword presence
    category_scores = {}
    for category in categories:
        keywords = category_keywords.get(category, [])
        score = sum(document_content.lower().count(keyword.lower()) for keyword in keywords)
        category_scores[category] = score
    
    # Sort categories by score (descending) - highest relevance first
    sorted_categories = sorted(categories, key=lambda x: category_scores[x], reverse=True)
    
    return sorted_categories

def run_comprehensive_analysis(client, rag_model):
    """Run comprehensive analysis on all processed documents with improved handling"""
    if not st.session_state.ocr_results:
        st.error("No documents to analyze. Please process documents first.")
        return False
    
    # Combine all document content
    combined_content = ""
    for idx, result in enumerate(st.session_state.ocr_results):
        file_name = st.session_state.file_names[idx]
        combined_content += f"\n\n=== DOCUMENT {idx+1}: {file_name} ===\n\n{result}\n\n"
    
    # Show document content statistics
    total_chars = len(combined_content)
    estimated_tokens = estimate_tokens(combined_content)
    st.info(f"📊 **Document Statistics:**\n"
           f"• Total characters: {total_chars:,}\n"
           f"• Estimated tokens: {estimated_tokens:,.0f}\n"
           f"• Documents: {len(st.session_state.ocr_results)}")
    
    # Define categories and questions
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
    
    # Prioritize categories based on document content
    category_order = prioritize_categories(combined_content, categories.keys())
    
    st.info(f"🎯 **Category Processing Order (by relevance):**\n" + 
           "\n".join([f"• {i+1}. {cat.title()}" for i, cat in enumerate(category_order)]))
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_categories = len(categories)
    
    # Process categories in order of relevance
    for idx, category in enumerate(category_order):
        questions = categories[category]
        try:
            progress = (idx + 1) / total_categories
            progress_bar.progress(progress)
            status_text.text(f"🔍 Analyzing {category.title()} information... ({idx+1}/{total_categories})")
            
            # Show processing info
            st.info(f"🔄 Processing **{category.title()}** category with **{len(questions)}** questions...")
            
            # Process the analysis
            analysis_result = process_analysis_questions(
                client, combined_content, questions, category, rag_model
            )
            
            # Add debug info to help track processing
            # with st.expander(f"🔍 Debug: Raw {category.title()} Response", expanded=False):
            #     st.text_area(
            #         f"Raw response for {category}:",
            #         analysis_result,
            #         height=200,
            #         key=f"debug_{category}"
            #     )
            
            # Parse the results
            parsed_results = parse_analysis_results(analysis_result)
            
            # Store results and show status
            if parsed_results:
                st.session_state.analysis_results[category] = parsed_results
                answered_questions = len([r for r in parsed_results if "No data available" not in r.get('answer', '')])
                st.success(f"✅ **{category.title()}** analysis completed! "
                          f"({len(parsed_results)} total results, {answered_questions} with data)")
            else:
                st.warning(f"⚠️ **{category.title()}** analysis returned no structured results")
                st.session_state.analysis_results[category] = []
            
            # Brief pause between categories
            time.sleep(1)
            
        except Exception as e:
            st.session_state.analysis_results[category] = []
            st.error(f"❌ Error analyzing **{category}**: {str(e)}")
    
    # Final summary
    progress_bar.progress(1.0)
    status_text.text("✅ Complete analysis finished!")
    
    # Calculate and display final statistics
    total_results = sum(len(results) for results in st.session_state.analysis_results.values())
    answered_results = 0
    
    for category, results in st.session_state.analysis_results.items():
        answered_count = len([r for r in results if "No data available" not in r.get('answer', '')])
        answered_results += answered_count
    
    st.success(f"🎉 **Analysis Complete!**\n"
              f"• Total questions processed: {total_results}\n"
              f"• Questions with answers: {answered_results}\n"
              f"• Success rate: {(answered_results/total_results*100):.1f}%" if total_results > 0 else "")
    
    # Show category-wise summary
    st.markdown("### 📊 Category Analysis Summary")
    for category in category_order:
        results = st.session_state.analysis_results.get(category, [])
        answered_count = len([r for r in results if "No data available" not in r.get('answer', '')])
        total_count = len(results)
        
        if answered_count > 0:
            st.markdown(f"✅ **{category.title()}**: {answered_count}/{total_count} questions answered")
        else:
            st.markdown(f"❌ **{category.title()}**: {answered_count}/{total_count} questions answered")
    
    # Mark analysis as completed
    st.session_state.analysis_completed = True
    
    # Clean up UI
    time.sleep(2)
    progress_bar.empty()
    status_text.empty()
    
    return True

def parse_analysis_results(analysis_text):
    """Parse the analysis results into structured format with improved handling of multiple formats"""
    results = []
    
    # Clean up the text first
    analysis_text = analysis_text.strip()
    
    # Try to split by different separators
    sections = []
    
    # Method 1: Split by --- separators
    if "---" in analysis_text:
        sections = analysis_text.split("---")
    else:
        # Method 2: Split by question patterns if no --- separators
        import re
        # Look for question patterns (both with and without asterisks)
        question_pattern = r'(?:\*\*Question[:\s]*\*\*|Question[:\s]*)'
        parts = re.split(question_pattern, analysis_text, flags=re.IGNORECASE)
        
        # Remove empty first part if it exists
        if parts and not parts[0].strip():
            parts = parts[1:]
        
        # Reconstruct sections with Question prefix
        sections = []
        for part in parts:
            if part.strip():
                sections.append("Question: " + part.strip())
    
    # Process each section
    for section in sections:
        if not section.strip():
            continue
            
        # Clean the section
        section = section.strip()
        
        # Initialize variables
        question = ""
        answer = ""
        source = ""
        
        # Split into lines for processing
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        
        current_field = None
        
        for line in lines:
            # Handle different question formats
            if (line.startswith("**Question") or 
                line.startswith("Question:") or 
                line.startswith("Question ")):
                
                # Extract question text
                if "**Question" in line:
                    # Handle **Question:** format
                    question_text = line.split("**", 2)[-1] if "**" in line else line
                    question_text = question_text.replace("Question:", "").strip()
                else:
                    # Handle Question: format
                    question_text = line.replace("Question:", "").strip()
                
                question = question_text
                current_field = "question"
                
            elif (line.startswith("**Answer") or 
                  line.startswith("Answer:") or 
                  line.startswith("Answer ")):
                
                # Extract answer text
                if "**Answer" in line:
                    # Handle **Answer:** format
                    answer_text = line.split("**", 2)[-1] if "**" in line else line
                    answer_text = answer_text.replace("Answer:", "").strip()
                else:
                    # Handle Answer: format
                    answer_text = line.replace("Answer:", "").strip()
                
                answer = answer_text
                current_field = "answer"
                
            elif (line.startswith("**Source") or 
                  line.startswith("Source:") or 
                  line.startswith("Source ")):
                
                # Extract source text
                if "**Source" in line:
                    # Handle **Source:** format
                    source_text = line.split("**", 2)[-1] if "**" in line else line
                    source_text = source_text.replace("Source:", "").strip()
                else:
                    # Handle Source: format
                    source_text = line.replace("Source:", "").strip()
                
                source = source_text
                current_field = "source"
                
            else:
                # Handle continuation lines
                if current_field == "question" and question:
                    question += " " + line
                elif current_field == "answer" and answer:
                    answer += " " + line
                elif current_field == "source" and source:
                    source += " " + line
        
        # Clean up the extracted text
        question = question.strip()
        answer = answer.strip()
        source = source.strip()
        
        # Only add if we have at least a question and answer
        if question and answer:
            results.append({
                "question": question,
                "answer": answer,
                "source": source if source else "Source not specified"
            })
    
    # If we still don't have results, try a more aggressive parsing approach
    if not results:
        # Look for any text that looks like Q&A pairs
        import re
        
        # Pattern to find question-answer pairs
        qa_pattern = r'(?:Question[:\s]*(?:\d+[:\.]?)?\s*)(.*?)(?:Answer[:\s]*)(.*?)(?:Source[:\s]*)(.*?)(?=Question|$)'
        matches = re.findall(qa_pattern, analysis_text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            if len(match) >= 2:
                question = match[0].strip()
                answer = match[1].strip()
                source = match[2].strip() if len(match) > 2 else "Source not specified"
                
                # Clean up asterisks and formatting
                question = re.sub(r'\*+', '', question).strip()
                answer = re.sub(r'\*+', '', answer).strip()
                source = re.sub(r'\*+', '', source).strip()
                
                if question and answer:
                    results.append({
                        "question": question,
                        "answer": answer,
                        "source": source if source else "Source not specified"
                    })
    
    return results

def display_all_questions_with_results(questions, results, category_name):
    """Display all questions for a category, showing results if available"""
    st.markdown(f"### {category_name} Questions & Analysis")

    # Create a mapping of questions to results for exact matching
    result_map = {}
    if results:
        for result in results:
            question_key = result['question'].strip().lower()
            result_map[question_key] = result
    
    # Also create a mapping by question index for fallback
    result_by_index = {}
    if results:
        for i, result in enumerate(results):
            result_by_index[i] = result

    # Display summary statistics
    answered_count = len([r for r in results if "No data available" not in r.get('answer', '')]) if results else 0
    total_count = len(questions)
    
    if answered_count > 0:
        st.success(f"📊 **Analysis Summary**: {answered_count}/{total_count} questions answered ({(answered_count/total_count*100):.1f}% success rate)")
    else:
        st.warning(f"📊 **Analysis Summary**: {answered_count}/{total_count} questions answered")

    # Display all questions
    for i, question in enumerate(questions, 1):
        with st.expander(f"Q{i}: {question[:80]}..." if len(question) > 80 else f"Q{i}: {question}", expanded=False):
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
                if "No data available" in answer or "not found" in answer.lower():
                    st.markdown(f"**Answer:** :red[{answer}]")
                elif any(word in answer.lower() for word in ['yes', 'present', 'contains', 'certified', 'compliant']):
                    st.markdown(f"**Answer:** :green[{answer}]")
                elif any(word in answer.lower() for word in ['no', 'free', 'not present', 'does not contain', 'absent']):
                    st.markdown(f"**Answer:** :blue[{answer}]")
                else:
                    st.markdown(f"**Answer:** {answer}")
                
                st.markdown(f"**Source:** {result['source']}")
            else:
                st.markdown("**Answer:** :orange[No specific analysis found for this question]")
                st.markdown("**Source:** :orange[Question not processed in current analysis]")

# [REST OF THE CODE REMAINS THE SAME - keeping all other functions unchanged]

def get_logo_base64():
    """Load and encode the logo"""
    logo_path = "Logo_Bayer.svg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_data = f.read()
            encoded_logo = base64.b64encode(logo_data).decode()
            return encoded_logo
    return None

def render_pdf_preview_scrollable(pdf_bytes, max_pages=10, page_width=600):
    """Render PDF pages as images for scrollable view - FIXED VERSION"""
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
        escaped_text = result.replace('"', '""').replace('\n', '\\n').replace('\r', '\\r')
        csv_content += f'{idx+1},"{file_name}",{len(result)},"{escaped_text}"\n'

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    download_links = [
        create_download_link(comprehensive_text, "text/plain", f"OCR_Results_Complete_{timestamp}.txt"),
        create_download_link(comprehensive_text, "text/markdown", f"OCR_Results_Complete_{timestamp}.md"),
        create_download_link(json_content, "application/json", f"OCR_Results_Complete_{timestamp}.json"),
        create_download_link(csv_content, "text/csv", f"OCR_Results_Complete_{timestamp}.csv")
    ]

    return download_links

def clean_api_key(api_key):
    """Clean the API key by removing any whitespace and 'Bearer' prefix."""
    if not api_key:
        return ""
    api_key = api_key.strip()
    api_key = re.sub(r'^Bearer\s+', '', api_key)
    return api_key

def validate_and_convert_image(file_bytes, file_name, mime_type):
    """Validate image format and convert PNG to JPEG if needed"""
    try:
        from PIL import Image
        import io
        
        if mime_type == "image/png" or file_name.lower().endswith('.png'):
            image = Image.open(io.BytesIO(file_bytes))
            
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=95)
            converted_bytes = output_buffer.getvalue()
            
            new_filename = file_name.rsplit('.', 1)[0] + '_converted.jpg'
            new_mime_type = "image/jpeg"
            
            return converted_bytes, new_filename, new_mime_type, True
        
        return file_bytes, file_name, mime_type, False
        
    except Exception as e:
        raise Exception(f"Error processing image: {str(e)}")

# Page configuration
st.set_page_config(
    page_title="Document Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Styling
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

/* Results header */
.results-header {
    display: flex;
    align-items: center;
    margin: 0.5rem 0 0.25rem 0 !important;
    font-size: 2rem;
    font-weight: 700;
    color: #1e293b;
    padding: 0.75rem !important;
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

/* Tab styling */
.custom-tabs-container {
    margin: 0 !important;
    padding: 0 !important;
    border-bottom: none;
    background: transparent;
}

div[data-testid="column"] .stButton > button {
    border: none !important;
    background: linear-gradient(135deg, #f1f5f9, #e2e8f0) !important;
    color: #64748b !important;
    padding: 12px 20px !important;
    margin: 0 2px !important;
    border-radius: 12px 12px 0 0 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    position: relative !important;
    z-index: 1 !important;
    min-height: 45px !important;
}

div[data-testid="column"] .stButton > button[kind="primary"] {
    border: none !important;
    background: linear-gradient(135deg, #4F8BF9, #3670CC) !important;
    color: white !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(79, 139, 249, 0.4) !important;
    z-index: 2 !important;
    transform: translateY(-1px) !important;
}

.analysis-header {
    background: linear-gradient(135deg, #4F8BF9, #3670CC);
    color: white;
    padding: 0.75rem !important;
    border-radius: 12px;
    margin-bottom: 0.5rem !important;
    text-align: center;
    font-weight: bold;
    font-size: 1.1rem;
    box-shadow: 0 4px 8px rgba(79, 139, 249, 0.3);
}

.excel-download-section {
    background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
    border: 2px solid #10b981;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    text-align: center;
}

.feature-highlight {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
}

.analysis-prompt {
    background: linear-gradient(135deg, #e0f2fe, #b3e5fc);
    border: 2px solid #0288d1;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    text-align: center;
}

/* PDF info styling */
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
if "analysis_completed" not in st.session_state:
    st.session_state.analysis_completed = False
# Add session state for the new comparison feature
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None


# CLEANED UP Sidebar configuration - Removed unwanted elements
with st.sidebar:
    st.markdown("<h2 class='sub-header'>⚙️ Configuration</h2>", unsafe_allow_html=True)

    # API key input
    api_key_input = st.text_input("🔑 Enter your Mistral API Key", type="password")
    api_key = clean_api_key(api_key_input)

    if not api_key:
        st.warning("⚠️ Please enter your API key to continue.")

    # Model selection for RAG
    rag_model = st.selectbox(
        "🤖 Select LLM for Analysis",
        ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-7b"],
        index=0
    )

    # File type selection
    file_type = st.radio("📄 Select file type", ("PDF", "Image"))
    source_type = st.radio("📂 Select source type", ("Local Upload", "URL"))

    # Processing options
    st.markdown("### 🔧 Processing Options")
    max_pdf_pages = st.slider("Max PDF pages to render", 1, 20, 10)
    pdf_page_width = st.slider("PDF page width (pixels)", 400, 800, 600)

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
    if file_type == "PDF":
        file_types = ["pdf"]
        help_text = "Upload PDF files only"
    else:
        file_types = ["jpg", "jpeg"]
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
        st.session_state.analysis_completed = False  # Reset analysis status
        st.session_state.comparison_results = None # Reset comparison results
        
        # Prepare sources
        sources = input_url.split("\n") if source_type == "URL" else uploaded_files
        sources = [s.strip() for s in sources if s.strip()] if source_type == "URL" else sources
        
        # Process each document
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
                        document = {"type": "image_url", "image_url": source}
                        preview_src = source
                        image_bytes = None
                    else:
                        file_bytes = source.read()
                        original_mime_type = source.type
                        
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
                            
                        except Exception as e:
                            st.error(f"Error processing image {source.name}: {str(e)}")
                            continue
                
                # Process with Mistral OCR
                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True
                )
                
                time.sleep(1)  # Rate limiting
                
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
                
                # Initialize chat history
                doc_id = str(uuid.uuid4())
                st.session_state.chat_history[doc_id] = []
                
            except Exception as e:
                st.error(f"Error processing {source_name}: {str(e)}")
                # Add empty entries to maintain consistency
                st.session_state.ocr_results.append(f"Error processing document: {str(e)}")
                st.session_state.preview_sources.append("")
                st.session_state.file_names.append(source_name if source_type == "URL" else source.name)
                st.session_state.pdf_bytes.append(None)
                st.session_state.image_bytes.append(None)
                doc_id = str(uuid.uuid4())
                st.session_state.chat_history[doc_id] = []
        
        progress_bar.progress(1.0)
        status_text.text("✅ OCR Processing complete!")
        st.session_state.processing_complete = True
        
        # Show completion message with next steps
        st.success("🎉 Document processing completed successfully!")
        st.info("💡 **Next Steps:**\n• View extracted text in **Document View** tab\n• Ask questions in **Question Answering** tab\n• Run detailed analysis in **Summary** tab\n• Generate Excel reports in **Excel Export** tab\n• Compare documents in the **Comparison** tab")
        
        time.sleep(2)
        progress_bar.empty()
        status_text.empty()

# Display results if available
if st.session_state.ocr_results:
    # Results Header
    st.markdown("""
    <div class="results-header">
        <div class="results-icon">📊</div>
        Results
    </div>
    """, unsafe_allow_html=True)

    # Tab Navigation
    st.markdown('<div class="custom-tabs-container">', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        doc_button_type = "primary" if st.session_state.active_tab == "document" else "secondary"
        if st.button("📄 Document View", 
                    key="tab_document",
                    use_container_width=True,
                    type=doc_button_type):
            st.session_state.active_tab = "document"
            st.rerun()

    with col2:
        qa_button_type = "primary" if st.session_state.active_tab == "qa" else "secondary"
        if st.button("💬 Question Answering", 
                    key="tab_qa",
                    use_container_width=True,
                    type=qa_button_type):
            st.session_state.active_tab = "qa"
            st.rerun()

    with col3:
        summary_button_type = "primary" if st.session_state.active_tab == "summary" else "secondary"
        if st.button("📈 Summary", 
                    key="tab_summary",
                    use_container_width=True,
                    type=summary_button_type):
            st.session_state.active_tab = "summary"
            st.rerun()

    with col4:
        tabular_button_type = "primary" if st.session_state.active_tab == "tabular" else "secondary"
        if st.button("📊 Excel Export", 
                    key="tab_tabular",
                    use_container_width=True,
                    type=tabular_button_type):
            st.session_state.active_tab = "tabular"
            st.rerun()

    with col5:
        comparison_button_type = "primary" if st.session_state.active_tab == "comparison" else "secondary"
        if st.button("⚖️ Comparison", 
                    key="tab_comparison",
                    use_container_width=True,
                    type=comparison_button_type):
            st.session_state.active_tab = "comparison"
            st.rerun()


    st.markdown('</div>', unsafe_allow_html=True)

    # Tab Content
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
        
        # Add comprehensive download section
        st.markdown("---")
        st.markdown("### 📥 Download Complete OCR Results")
        st.markdown("Download all extracted text from all processed documents in various formats:")
        
        comprehensive_downloads = create_comprehensive_download_options(
            st.session_state.ocr_results, 
            st.session_state.file_names
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📄 Text Formats:**")
            if len(comprehensive_downloads) >= 2:
                st.markdown(comprehensive_downloads[0], unsafe_allow_html=True)
                st.markdown(comprehensive_downloads[1], unsafe_allow_html=True)
        
        with col2:
            st.markdown("**📊 Data Formats:**")
            if len(comprehensive_downloads) >= 4:
                st.markdown(comprehensive_downloads[2], unsafe_allow_html=True)
                st.markdown(comprehensive_downloads[3], unsafe_allow_html=True)
        
        total_chars = sum(len(result) for result in st.session_state.ocr_results)
        st.info(f"📊 **Summary:** {len(st.session_state.ocr_results)} documents - {total_chars:,} total characters extracted")

    elif st.session_state.active_tab == "tabular":
        # Simplified Excel Export Tab - Direct Generation Only
        # st.markdown("### 📊 Excel Export")
        
        if not st.session_state.ocr_results:
            st.warning("⚠️ No documents processed yet. Please process documents first.")
        else:
            # Initialize Mistral client for LLM processing
            try:
                client = Mistral(api_key=api_key)
            except:
                client = None
                st.error("❌ Unable to initialize LLM client. Please check your API key.")
        
        if client:
            # Simple Excel Generation Section
            # st.markdown('<div class="excel-download-section">', unsafe_allow_html=True)
            st.markdown("### 📥 Generate Excel Report")
            # st.markdown("Extract tabular data from all documents and create a professional Excel report.")
            
            # Show summary of what will be processed
            st.markdown(f"""
            **📋 Ready to Process:**
            - 📄 **{len(st.session_state.ocr_results)} documents** will be analyzed
            - 🤖 **AI-powered extraction** will find all tables and data
            - 📊 **Professional Excel format** with proper formatting
            - ⚡ **Fast processing** using optimized LLM approach
            """)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                if st.button("📊 Generate Excel Report", 
                            key="generate_excel_simple", 
                            use_container_width=True,
                            type="primary"):
                    
                    with st.spinner("🔄 Extracting tabular data and creating Excel report..."):
                        try:
                            if not EXCEL_AVAILABLE:
                                st.error("❌ Excel functionality not available. Please install openpyxl: `pip install openpyxl`")
                            else:
                                # Import the new function
                                from tabular import create_simple_excel_export
                                
                                excel_data = create_simple_excel_export(
                                    st.session_state.ocr_results,
                                    st.session_state.file_names,
                                    client,
                                    rag_model
                                )
                                
                                if excel_data:
                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                    filename = f"Tabular_Data_Report_{timestamp}.xlsx"
                                    
                                    st.download_button(
                                        label="📥 Download Excel Report",
                                        data=excel_data,
                                        file_name=filename,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_excel_simple",
                                        use_container_width=True
                                    )
                                    
                                    st.success("✅ Excel report generated successfully!")
                                    
                                    # Show what was included
                                    file_size_mb = len(excel_data) / (1024 * 1024)
                                    st.info(f"📊 File size: {file_size_mb:.2f} MB | Documents: {len(st.session_state.ocr_results)}")
                                    
                                    st.markdown("**✅ Report includes:**")
                                    st.markdown("• All tabular data extracted using AI")
                                    st.markdown("• Proper column headers and clean values")
                                    st.markdown("• Document analysis and summaries")
                                    st.markdown("• Professional Excel formatting")
                                    st.markdown("• Individual sheets + consolidated summary")
                                    
                                else:
                                    st.error("❌ No tabular data could be extracted from the documents")
                                    st.info("💡 Try uploading documents with clear table structures")
                                    
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            st.info("💡 Make sure you have a valid API key and try again.")
            
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "qa":
        st.markdown("### 💬 Question Answering")

        # Document selection with "All Documents" option
        if len(st.session_state.ocr_results) > 1:
            doc_options = ["📚 All Documents"] + [f"📄 Document {i+1}: {st.session_state.file_names[i]}" for i in range(len(st.session_state.file_names))]
        
            selected_option = st.selectbox(
                "📂 Select document to query:",
                range(len(doc_options)),
                format_func=lambda i: doc_options[i],
                key="doc_selector_qa"
            )
        
            is_all_documents = (selected_option == 0)
            selected_doc = selected_option - 1 if not is_all_documents else None
        
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

            # Question input
            placeholder_text = "Ask a question about all documents..." if is_all_documents else "What is this document about?"

            clear_input_flag = f"clear_input_{doc_id}"
            if clear_input_flag not in st.session_state:
                st.session_state[clear_input_flag] = False

            if st.session_state[clear_input_flag]:
                input_value = ""
                st.session_state[clear_input_flag] = False
            else:
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
                    use_container_width=True
                )
            with col2:
                clear_history = st.button(
                    "🗑️ Clear History", 
                    key=f"clear_{doc_id}",
                    use_container_width=True
                )

            if submit_question and user_question.strip():
                with st.spinner("🤔 Processing your question..."):
                    st.session_state.chat_history[doc_id].append({
                        "role": "user",
                        "content": user_question
                    })

                    if is_all_documents:
                        combined_content = ""
                        for idx, result in enumerate(st.session_state.ocr_results):
                            file_name = st.session_state.file_names[idx]
                            combined_content += f"\n\n=== DOCUMENT {idx+1}: {file_name} ===\n\n{result}\n\n"
                        document_content = combined_content
                        context_info = f"all {len(st.session_state.ocr_results)} documents"
                    else:
                        document_content = st.session_state.ocr_results[selected_doc]
                        context_info = f"the document '{st.session_state.file_names[selected_doc]}'"

                    system_prompt = f"""You are a helpful assistant that answers questions based on the provided document(s).

Document content:
{document_content}

Answer questions based ONLY on the information in the document(s). When referencing information, please mention which document it comes from when applicable. If the answer is not in the document(s), say "I don't have enough information to answer that question based on the document content." Be concise and accurate.

You are currently analyzing {context_info}."""

                    messages = [{"role": "system", "content": system_prompt}]
                    for msg in st.session_state.chat_history[doc_id]:
                        messages.append({"role": msg["role"], "content": msg["content"]})

                    try:
                        client = Mistral(api_key=api_key)
                        chat_response = client.chat.complete(
                            model=rag_model,
                            messages=messages
                        )

                        assistant_response = chat_response.choices[0].message.content
                        st.session_state.chat_history[doc_id].append({
                            "role": "assistant",
                            "content": assistant_response
                        })
                    
                        st.session_state[clear_input_flag] = True
                        st.success("✅ Question processed successfully!")
                        time.sleep(0.5)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")

            elif submit_question and not user_question.strip():
                st.warning("Please enter a question before submitting.")

            if clear_history:
                with st.spinner("🗑️ Clearing chat history..."):
                    st.session_state.chat_history[doc_id] = []
                    st.session_state[clear_input_flag] = True
                    st.success("🗑️ Chat history cleared!")
                    time.sleep(0.5)
                    st.rerun()

    elif st.session_state.active_tab == "summary":
        st.markdown("### 📈 Summary & Analysis")
        
        # Check if analysis has been completed
        if not st.session_state.analysis_completed:
            # Show analysis prompt
            st.markdown("""
            <div class="analysis-prompt">
                <h4>🔍 Comprehensive Document Analysis</h4>
                <p><strong>Ready to analyze your documents:</strong></p>
                <ul>
                    <li>📊 <strong>{} documents</strong> processed and ready for analysis</li>
                    <li>🎯 <strong>8 specialized categories</strong> will be analyzed</li>
                    <li>❓ <strong>Multiple questions</strong> per category for comprehensive insights</li>
                    <li>⏱️ <strong>Analysis time:</strong> ~2-3 minutes depending on document complexity</li>
                </ul>
                <p>Click the button below to start the comprehensive analysis.</p>
            </div>
            """.format(len(st.session_state.ocr_results)), unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Start Comprehensive Analysis", 
                            key="start_analysis", 
                            use_container_width=True,
                            type="primary"):
                    try:
                        client = Mistral(api_key=api_key)
                        success = run_comprehensive_analysis(client, rag_model)
                        if success:
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error initializing analysis: {str(e)}")
            
            # Show what will be analyzed
            st.markdown("---")
            st.markdown("### 📋 Analysis Categories")
            
            categories_info = [
                ("🥗 Nutrient Analysis", f"{len(NUTRIENT_QUESTIONS)} questions", "Energy, protein, fat, carbohydrates, vitamins, minerals"),
                ("🌱 Dietary Information", f"{len(DIETARY_QUESTIONS)} questions", "Halal, Kosher, Vegan, Gluten-free, Natural flavoring"),
                ("⚠️ Allergen Information", f"{len(ALLERGEN_QUESTIONS)} questions", "14 major allergens, cross-contamination risks"),
                ("🧬 GMO Analysis", f"{len(GMO_QUESTIONS)} questions", "Genetic modification, labeling requirements, regulations"),
                ("🛡️ Safety Analysis", f"{len(SAFETY_QUESTIONS)} questions", "Heavy metals, irradiation, contaminants, residues"),
                ("🧪 Composition Analysis", f"{len(COMPOSITION_QUESTIONS)} questions", "Ingredients, percentages, carrier components"),
                ("🦠 Microbiological", f"{len(MICROBIOLOGICAL_QUESTIONS)} questions", "Microbial counts, pathogens, shelf life, storage"),
                ("📋 Regulatory Compliance", f"{len(REGULATORY_QUESTIONS)} questions", "EU regulations, BPOM, food grade requirements")
            ]
            
            col1, col2 = st.columns(2)
            
            for i, (category, question_count, description) in enumerate(categories_info):
                with col1 if i % 2 == 0 else col2:
                    st.markdown(f"""
                    **{category}** 📊 {question_count}  
                    💡 {description}
                    """)
        
        else:
            # Analysis completed - show results with tabs
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

            # Add option to re-run analysis
            col1, col2, col3 = st.columns([3, 1, 1])
            with col2:
                if st.button("🔄 Re-run Analysis", 
                            key="rerun_analysis",
                            use_container_width=True):
                    st.session_state.analysis_completed = False
                    st.session_state.analysis_results = {}
                    st.rerun()

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
                    categories = ["nutrient", "dietary", "allergen", "gmo", "safety", "composition", "microbiological", "regulatory"]
                    for category in categories:
                        if category in st.session_state.analysis_results:
                            count = len(st.session_state.analysis_results[category])
                            answered_count = len([r for r in st.session_state.analysis_results[category] if "No data available" not in r.get('answer', '')])
                            st.markdown(f"✅ {category.title()}: {answered_count}/{count} questions answered")
                        else:
                            st.markdown(f"❌ {category.title()}: Not analyzed")
                else:
                    st.info("No structured analysis performed yet. Click 'Start Comprehensive Analysis' to begin.")
            
            elif st.session_state.active_summary_tab == "nutrient":
                st.markdown('<div class="analysis-header">🥗 Nutrient Composition Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("nutrient", [])
                display_all_questions_with_results(NUTRIENT_QUESTIONS, results, "Nutrient Composition")
            
            elif st.session_state.active_summary_tab == "dietary":
                st.markdown('<div class="analysis-header">🌱 Dietary Information Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("dietary", [])
                display_all_questions_with_results(DIETARY_QUESTIONS, results, "Dietary Information")
            
            elif st.session_state.active_summary_tab == "allergen":
                st.markdown('<div class="analysis-header">⚠️ Allergen Information Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("allergen", [])
                display_all_questions_with_results(ALLERGEN_QUESTIONS, results, "Allergen Information")
            
            elif st.session_state.active_summary_tab == "gmo":
                st.markdown('<div class="analysis-header">🧬 GMO Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("gmo", [])
                display_all_questions_with_results(GMO_QUESTIONS, results, "GMO Information")
            
            elif st.session_state.active_summary_tab == "safety":
                st.markdown('<div class="analysis-header">🛡️ Safety Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("safety", [])
                display_all_questions_with_results(SAFETY_QUESTIONS, results, "Safety Information")
            
            elif st.session_state.active_summary_tab == "composition":
                st.markdown('<div class="analysis-header">🧪 Composition Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("composition", [])
                display_all_questions_with_results(COMPOSITION_QUESTIONS, results, "Composition Information")
            
            elif st.session_state.active_summary_tab == "microbiological":
                st.markdown('<div class="analysis-header">🦠 Microbiological Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("microbiological", [])
                display_all_questions_with_results(MICROBIOLOGICAL_QUESTIONS, results, "Microbiological Information")
            
            elif st.session_state.active_summary_tab == "regulatory":
                st.markdown('<div class="analysis-header">📋 Regulatory Analysis</div>', unsafe_allow_html=True)
                results = st.session_state.analysis_results.get("regulatory", [])
                display_all_questions_with_results(REGULATORY_QUESTIONS, results, "Regulatory Information")

    elif st.session_state.active_tab == "comparison":
        # This is where the new comparison tab will be rendered
        try:
            client = Mistral(api_key=api_key)
            render_comparison_tab(
                client, 
                rag_model, 
                st.session_state.ocr_results, 
                st.session_state.file_names
            )
        except Exception as e:
            st.error(f"Error initializing Mistral client for comparison: {e}")


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
            <p style="margin: 0; font-size: 0.8rem; color: #94a3b8;">© 2025 EY. All rights reserved.</p>
        </footer>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown("<p style='text-align: center; color: #64748b;'>Document Intelligence System - Extract, analyze, and query documents using advanced OCR and RAG capabilities</p>", unsafe_allow_html=True)
