import streamlit as st
import time
from mistralai import Mistral
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

def run_comprehensive_analysis(client, rag_model):
    """Run comprehensive analysis on all processed documents"""
    if not st.session_state.ocr_results:
        st.error("No documents to analyze. Please process documents first.")
        return False
    
    # Combine all document content
    combined_content = ""
    for idx, result in enumerate(st.session_state.ocr_results):
        file_name = st.session_state.file_names[idx]
        combined_content += f"\n\n=== DOCUMENT {idx+1}: {file_name} ===\n\n{result}\n\n"
    
    # Run analysis for each category
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
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_categories = len(categories)
    
    for idx, (category, questions) in enumerate(categories.items()):
        try:
            progress = (idx + 1) / total_categories
            progress_bar.progress(progress)
            status_text.text(f"🔍 Analyzing {category.title()} information... ({idx+1}/{total_categories})")
            
            analysis_result = process_analysis_questions(
                client, combined_content, questions, category, rag_model
            )
            parsed_results = parse_analysis_results(analysis_result)
            
            if parsed_results:
                st.session_state.analysis_results[category] = parsed_results
                st.success(f"✅ {category.title()} analysis completed! ({len(parsed_results)} results)")
            else:
                st.warning(f"⚠️ {category.title()} analysis returned no results")
                st.session_state.analysis_results[category] = []
            
            time.sleep(1)
        except Exception as e:
            st.session_state.analysis_results[category] = []
            st.error(f"Error analyzing {category}: {str(e)}")
    
    progress_bar.progress(1.0)
    status_text.text("✅ Complete analysis finished!")
    total_results = sum(len(results) for results in st.session_state.analysis_results.values())
    st.info(f"📊 Analysis complete! Total results: {total_results}")
    
    # Mark analysis as completed
    st.session_state.analysis_completed = True
    
    time.sleep(1)
    progress_bar.empty()
    status_text.empty()
    
    return True

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
                st.markdown("**Answer:** :orange[No specific analysis found for this question]")
                st.markdown("**Source:** :orange[Question not processed in current analysis]")

def render_summary_tab(api_key, rag_model):
    """Render the Summary tab functionality"""
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
                **{category}**  
                📊 {question_count}  
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
                        st.markdown(f"✅ {category.title()}: {count} questions analyzed")
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
