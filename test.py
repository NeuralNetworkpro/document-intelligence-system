import streamlit as st
import pandas as pd
import io
import json
import base64
import re
from mistralai import Mistral
from datetime import datetime
import time

def parse_source_of_truth_file(upload_file):
    """Parses the uploaded master Excel file."""
    file_name = upload_file.name
    if file_name.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(upload_file, header=None)
            if df.shape[1] < 2:
                st.error("The master Excel file must have at least two columns.")
                return None
            df.rename(columns={0: 'Attribute', 1: 'Value'}, inplace=True)
            df.dropna(subset=['Attribute'], inplace=True)
            df['Value'] = df['Value'].ffill().astype(str)
            source_of_truth = pd.Series(df.Value.values, index=df.Attribute).to_dict()
            return source_of_truth
        except Exception as e:
            st.error(f"Error reading the Excel file: {e}")
            return None
    else:
        st.error("Unsupported file type for Master File. Please upload an Excel (.xlsx, .xls) file.")
        return None

def create_single_document_comparison_prompt(master_file_data, single_source_document_text, source_document_name):
    """
    Creates a detailed, intelligent prompt for the LLM to perform a robust, context-aware comparison
    and return a structured JSON object.
    """
    master_data_str = "\n".join([f"- {key}: {value}" for key, value in master_file_data.items()])

    # This is the new, highly specific prompt designed to prevent logical errors and force JSON output.
    return f"""
Your Role:
You are a senior Data Quality Analyst specializing in pharmaceutical GxP documentation. You are an expert at identifying subtle but critical discrepancies between supplier documents and internal master data. Your work is audited, so precision and clear reasoning are paramount.

Objective:
Perform a meticulous, field-by-field comparison between a given Source Document and a Master File. Identify and report every match and mismatch with absolute precision. Your entire output MUST be a single, valid JSON object.

Inputs:
1.  **Source Document:** The single file to be analyzed. Its content is provided below.
    --- SOURCE DOCUMENT: {source_document_name} ---
    {single_source_document_text}
    --- END SOURCE DOCUMENT ---

2.  **Master File:** The central spreadsheet to compare against. Its data is provided below.
    --- MASTER FILE DATA ---
    {master_data_str}
    --- END MASTER FILE DATA ---

**CRITICAL ANALYSIS & COMPARISON RULES:**

1.  **Field Matching:** For each `[Field Name]` from the Master File, first find the most plausible corresponding field in the Source Document. Use semantic matching (e.g., "Product Name" in master matches "Material Description" in source).

2.  **Data Type Identification:** Before comparing, identify the data type for both the Source Value and Master File Value (e.g., Date, String, Number, Version, Person's Name, Specification Range).

3.  **Value Normalization (MANDATORY):** Before comparison, you MUST normalize the values:
    * **Dates:** Convert all dates to a standard `YYYY-MM-DD` format. Handle various formats like `Mar-19-2019`, `19.03.2019`, `5 September 2018`.
    * **Text & Codes:** Trim all leading/trailing whitespace. Comparison should be case-insensitive. `Rev.6.0` is identical to `Rev. 6.0`.
    * **Country Codes:** Recognize standard ISO codes are equivalent to full names (e.g., `ID` is the same as `Indonesia`).
    * **Placeholder/Null Values:** Treat values like `9999-12-31 00:00:00`, `N/A`, `Not specified`, or empty cells as "placeholder/null".

4.  **Intelligent Comparison Logic:**
    * **Compare Normalized Values:** Perform the final comparison on the *normalized* values.
    * **Prevent Invalid Comparisons:** If the identified data types are incompatible (e.g., a person's name vs. a date), you MUST NOT compare them. Instead, report a `Data Type Mismatch`.
    * **Handle Placeholders:** If the Master File contains a placeholder value (like `9999-12-31`), and the Source Document has a valid value, this is a `Mismatch`.

**Required Output Format:**
Generate a single JSON object as your response. The JSON object should contain three keys: "comparison_findings", "mismatches", and "matches".

{{
  "comparison_findings": "A 1-2 sentence overview of the findings for this specific document.",
  "mismatches": [
    {{
      "field_name": "The name of the mismatched field from the Master File.",
      "reason": "A clear explanation of *why* it's a mismatch based on the rules. E.g., 'Normalized dates do not match,' or 'Incompatible data types found.'",
      "source_value": "The value from the Source Document.",
      "master_value": "The value from the Master File."
    }}
  ],
  "matches": [
    {{
      "field_name": "The name of the matched field.",
      "value": "The confirmed matching value."
    }}
  ],
  "summary": "A final, concise summary. Bold the most critical discrepancies using Markdown (**critical discrepancy**) and state the overall implication."
}}
"""

def run_comparison_for_all_docs(client, model, master_file_data, ocr_results, file_names):
    """
    Loops through each OCR'd document, runs a comparison against the master file,
    and collects the generated JSON reports. Includes retry logic for API rate limiting.
    """
    all_reports = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_docs = len(ocr_results)
    max_retries = 5
    initial_backoff = 2  # seconds

    for i, (source_doc_text, source_doc_name) in enumerate(zip(ocr_results, file_names)):
        progress = (i + 1) / total_docs
        status_text.text(f"🤖 Analyzing document {i+1}/{total_docs}: {source_doc_name}...")
        
        prompt = create_single_document_comparison_prompt(master_file_data, source_doc_text, source_doc_name)
        
        for attempt in range(max_retries):
            try:
                response = client.chat.complete(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"} # Force JSON output
                )
                report_content = json.loads(response.choices[0].message.content)
                all_reports.append({
                    "document_name": source_doc_name,
                    "report": report_content
                })
                break 
            except Exception as e:
                if "429" in str(e):
                    if attempt < max_retries - 1:
                        backoff_time = initial_backoff * (2 ** attempt)
                        status_text.warning(f"Rate limit hit for {source_doc_name}. Retrying in {backoff_time} seconds...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        st.error(f"Failed to analyze {source_doc_name} after multiple retries due to API rate limits.")
                        all_reports.append({"document_name": source_doc_name, "report": {"error": "API service capacity exceeded."}})
                        break
                else:
                    st.error(f"An unexpected error occurred while analyzing {source_doc_name}: {e}")
                    all_reports.append({"document_name": source_doc_name, "report": {"error": f"An unexpected error occurred: {e}"}})
                    break
        
        progress_bar.progress(progress)

    status_text.success("✅ All documents analyzed!")
    time.sleep(2)
    status_text.empty()
    progress_bar.empty()
    return all_reports

def parse_report_to_summary_df(results):
    """Parses all reports to create a high-level summary DataFrame."""
    summary_data = []
    for result in results:
        doc_name = result.get("document_name", "N/A")
        report = result.get("report", {})
        
        num_mismatches = len(report.get("mismatches", []))
        num_matches = len(report.get("matches", []))
        status = "✅ Pass" if num_mismatches == 0 else "⚠️ Needs Review"
        
        summary_data.append({
            "Document Name": doc_name,
            "Mismatches": num_mismatches,
            "Matches": num_matches,
            "Overall Status": status
        })
    return pd.DataFrame(summary_data)

def prepare_data_for_export(results, master_file_name):
    """Prepares the structured data for CSV/Excel export."""
    export_data = []
    for result in results:
        doc_name = result.get("document_name", "N/A")
        report = result.get("report", {})
        
        export_data.append({
            "Source Document": doc_name,
            "Master File": master_file_name,
            "Overview": report.get("comparison_findings", "N/A"),
            "Mismatches": json.dumps(report.get("mismatches", [])),
            "Matches": json.dumps(report.get("matches", [])),
            "Final Summary": report.get("summary", "N/A")
        })
    return pd.DataFrame(export_data)

def render_comparison_tab(client, rag_model, ocr_results, file_names):
    """
    Renders the main Comparison tab, generating a detailed report table
    for each source document against the master file.
    """
    st.markdown("### ⚖️ Document Compliance Verification")
    
    if not ocr_results:
        st.warning("Please process at least one document on the main page before running a comparison.")
        return

    st.info("Upload a master Excel file to validate against the processed documents.")
    master_file = st.file_uploader("📤 Upload your Master File (Excel)", type=['xlsx', 'xls'], key="master_file_uploader")

    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = None

    if master_file:
        if st.button("🚀 Run Compliance Verification", use_container_width=True, type="primary"):
            st.session_state.comparison_results = None
            
            with st.spinner("Parsing master file..."):
                master_data = parse_source_of_truth_file(master_file)
            
            if master_data:
                reports = run_comparison_for_all_docs(client, rag_model, master_data, ocr_results, file_names)
                
                if reports:
                    st.session_state.comparison_results = reports
                    st.success("✅ Compliance Verification Report Generated!")
                else:
                    st.error("❌ Comparison failed. The AI could not generate any reports.")

    if st.session_state.comparison_results:
        results = st.session_state.comparison_results
        
        st.markdown("---")
        st.markdown("### 📊 At-a-Glance Summary")
        
        summary_df = parse_report_to_summary_df(results)
        def style_status(status):
            return 'background-color: #f8d7da; color: #721c24' if status == '⚠️ Needs Review' else 'background-color: #d4edda; color: #155724'
        # FIX: Updated to use .map() to resolve FutureWarning
        st.dataframe(summary_df.style.map(style_status, subset=['Overall Status']), use_container_width=True)

        st.markdown("---")
        st.markdown("### 📋 Detailed Validation Report")

        # NEW UI: Display each report in a styled, expandable container
        for result in results:
            doc_name = result.get("document_name", "Unknown Document")
            report = result.get("report", {})

            with st.expander(f"**{doc_name}** vs. **{master_file.name}**", expanded=True):
                st.markdown(f"##### Comparison Findings")
                st.write(report.get("comparison_findings", "No overview provided."))
                
                # Mismatches Section
                mismatches = report.get("mismatches", [])
                if mismatches:
                    st.markdown('<div style="background-color: #f8d7da; border-left: 5px solid #721c24; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
                                '<h5>❌ Mismatches Detected</h5>', unsafe_allow_html=True)
                    for item in mismatches:
                        st.markdown(f"**{item.get('field_name', 'N/A')}:** {item.get('reason', 'No reason provided.')}")
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;*Source Value:* `{item.get('source_value', 'N/A')}`")
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;*Master File Value:* `{item.get('master_value', 'N/A')}`")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Matches Section
                matches = report.get("matches", [])
                if matches:
                    st.markdown('<div style="background-color: #d4edda; border-left: 5px solid #155724; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
                                '<h5>✅ Matches Confirmed</h5>', unsafe_allow_html=True)
                    match_list = [f"- **{item.get('field_name', 'N/A')}:** `{item.get('value', 'N/A')}`" for item in matches]
                    st.markdown("\n".join(match_list))
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Summary Section
                st.markdown('<div style="background-color: #d1ecf1; border-left: 5px solid #0c5460; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
                            '<h5>📝 Summary</h5>', unsafe_allow_html=True)
                st.markdown(report.get("summary", "No summary provided."))
                st.markdown('</div>', unsafe_allow_html=True)

        # --- Download Option ---
        st.markdown("---")
        st.markdown("#### 📥 Download Full Report")
        
        df_export = prepare_data_for_export(results, master_file.name)
        csv = df_export.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="📥 Download Report (CSV)",
            data=csv,
            file_name=f"consolidated_report_{master_file.name}.csv",
            mime="text/csv",
            use_container_width=True
        )
