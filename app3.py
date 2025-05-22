import streamlit as st
from PIL import Image
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="Bayer Document Intelligence System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
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
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 2rem;
        background-color: white;
        border-bottom: 1px solid #eee;
    }
    
    .logo-title {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    /* Hero section styling */
    .hero-container {
        background: linear-gradient(135deg, var(--bayer-light-blue) 0%, var(--bayer-light-green) 100%);
        padding: 3rem 2rem;
        border-radius: 0 0 10px 10px;
        margin-bottom: 2rem;
    }
    
    .hero-title {
        color: var(--bayer-blue);
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .hero-subtitle {
        color: #444;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        max-width: 800px;
    }
    
    /* Feature card styling */
    .features-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        padding: 0 2rem;
    }
    
    .feature-card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
    }
    
    .feature-title {
        color: var(--bayer-blue);
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .feature-description {
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Stats section styling */
    .stats-container {
        margin-top: 3rem;
        padding: 2rem;
        background-color: var(--bayer-light-blue);
        border-radius: 10px;
    }
    
    /* Button styling */
    .custom-button {
        background-color: var(--bayer-blue);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 5px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
        text-decoration: none;
        display: inline-block;
    }
    
    .custom-button:hover {
        background-color: #002a7d;
    }
    
    .custom-button-secondary {
        background-color: white;
        color: var(--bayer-blue);
        border: 1px solid var(--bayer-blue);
    }
    
    .custom-button-secondary:hover {
        background-color: #f8f9fa;
    }
    
    /* Footer styling */
    .footer {
        margin-top: 4rem;
        padding: 2rem;
        background-color: #f8f9fa;
        text-align: center;
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Metrics styling */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--bayer-blue);
    }
    
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    
    /* Login form styling */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2rem;
        }
        
        .hero-subtitle {
            font-size: 1rem;
        }
        
        .features-container {
            grid-template-columns: 1fr;
        }
    }
</style>
""", unsafe_allow_html=True)

# Header with logo and navigation
st.markdown("""
<div class="header-container">
    <div class="logo-title">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Bayer_Logo.svg/1200px-Bayer_Logo.svg.png" height="40">
        <h2>Document Intelligence</h2>
    </div>
    <div>
        <a href="#" class="custom-button custom-button-secondary">Sign In</a>
        <a href="#" class="custom-button">Get Started</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">Transform Your Document Workflows</h1>
    <p class="hero-subtitle">
        Bayer's Document Intelligence System leverages advanced AI to extract insights, 
        automate classification, and streamline document processing across the organization.
    </p>
    <a href="#" class="custom-button">Explore Features</a>
    <a href="#" class="custom-button custom-button-secondary" style="margin-left: 10px;">Watch Demo</a>
</div>
""", unsafe_allow_html=True)

# Main content - Features section
st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Key Capabilities</h2>", unsafe_allow_html=True)

st.markdown("""
<div class="features-container">
    <div class="feature-card">
        <div class="feature-title">📄 Document Classification</div>
        <p class="feature-description">
            Automatically categorize documents using advanced machine learning algorithms with 98% accuracy.
        </p>
    </div>
    <div class="feature-card">
        <div class="feature-title">🔍 Information Extraction</div>
        <p class="feature-description">
            Extract key data points from documents including tables, forms, and unstructured text.
        </p>
    </div>
    <div class="feature-card">
        <div class="feature-title">🔄 Workflow Automation</div>
        <p class="feature-description">
            Create intelligent workflows that route documents based on content, priority, and business rules.
        </p>
    </div>
    <div class="feature-card">
        <div class="feature-title">📊 Analytics Dashboard</div>
        <p class="feature-description">
            Gain insights into document processing metrics, bottlenecks, and optimization opportunities.
        </p>
    </div>
    <div class="feature-card">
        <div class="feature-title">🔒 Compliance & Security</div>
        <p class="feature-description">
            Ensure regulatory compliance with audit trails, access controls, and secure document handling.
        </p>
    </div>
    <div class="feature-card">
        <div class="feature-title">🌐 Enterprise Integration</div>
        <p class="feature-description">
            Seamlessly connect with existing Bayer systems including SAP, SharePoint, and custom applications.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# System metrics visualization
st.markdown("<div class='stats-container'>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>System Performance</h2>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>98%</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Classification Accuracy</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>85%</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Time Saved</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>10x</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Processing Speed</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>24/7</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>System Availability</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Sample data for visualization
data = {
    'Document Type': ['Contracts', 'Invoices', 'Reports', 'Forms', 'Emails'],
    'Processing Time (sec)': [2.3, 1.8, 3.5, 1.2, 0.9],
    'Accuracy (%)': [98, 99, 95, 97, 94],
    'Volume': [1200, 3500, 850, 2200, 5000]
}

df = pd.DataFrame(data)

# Create a bubble chart
fig = px.scatter(
    df, 
    x='Processing Time (sec)', 
    y='Accuracy (%)', 
    size='Volume',
    color='Document Type',
    color_discrete_sequence=px.colors.qualitative.Bold,
    hover_name='Document Type',
    size_max=60,
    title='Document Processing Performance by Type'
)

fig.update_layout(
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=20, r=20, t=40, b=20),
    font=dict(size=12)
)

st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# Demo section
st.markdown("<h2 style='text-align: center; margin: 3rem 0 2rem;'>See It In Action</h2>", unsafe_allow_html=True)

demo_col1, demo_col2 = st.columns([2, 1])

with demo_col1:
    st.image("https://placeholder.svg?height=300&width=600&query=Document+Intelligence+Dashboard+Visualization", 
             caption="Document Intelligence Dashboard")
    
with demo_col2:
    st.markdown("""
    <div style="padding: 1rem;">
        <h3 style="color: var(--bayer-blue);">Streamlined Document Processing</h3>
        <p style="margin-bottom: 1rem;">
            Watch how our system processes various document types, extracts critical information, 
            and routes them through appropriate workflows.
        </p>
        <ul style="margin-bottom: 1.5rem;">
            <li>Automated document classification</li>
            <li>Intelligent data extraction</li>
            <li>Workflow automation</li>
            <li>Real-time analytics</li>
        </ul>
        <a href="#" class="custom-button">Watch Full Demo</a>
    </div>
    """, unsafe_allow_html=True)

# Testimonials
st.markdown("<h2 style='text-align: center; margin: 3rem 0 2rem;'>What Our Users Say</h2>", unsafe_allow_html=True)

testimonial_col1, testimonial_col2, testimonial_col3 = st.columns(3)

with testimonial_col1:
    st.markdown("""
    <div style="background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%;">
        <p style="font-style: italic; color: #555;">"The document intelligence system has transformed how our research team manages scientific publications and reports. We've reduced processing time by 80%."</p>
        <p style="color: var(--bayer-blue); font-weight: 600; margin-top: 1rem;">Dr. Sarah Chen</p>
        <p style="color: #777; font-size: 0.9rem;">Research Director, Crop Science</p>
    </div>
    """, unsafe_allow_html=True)

with testimonial_col2:
    st.markdown("""
    <div style="background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%;">
        <p style="font-style: italic; color: #555;">"Implementing this system has streamlined our regulatory submission process. What used to take weeks now happens in days with greater accuracy."</p>
        <p style="color: var(--bayer-blue); font-weight: 600; margin-top: 1rem;">Michael Rodriguez</p>
        <p style="color: #777; font-size: 0.9rem;">Compliance Manager, Pharmaceuticals</p>
    </div>
    """, unsafe_allow_html=True)

with testimonial_col3:
    st.markdown("""
    <div style="background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%;">
        <p style="font-style: italic; color: #555;">"The analytics capabilities have given us unprecedented visibility into our document workflows, helping us identify and eliminate bottlenecks."</p>
        <p style="color: var(--bayer-blue); font-weight: 600; margin-top: 1rem;">Emma Schultz</p>
        <p style="color: #777; font-size: 0.9rem;">Operations Director, Global Supply Chain</p>
    </div>
    """, unsafe_allow_html=True)

# Call to action
st.markdown("""
<div style="text-align: center; margin: 4rem 0; padding: 3rem; background: linear-gradient(135deg, var(--bayer-light-blue) 0%, var(--bayer-light-green) 100%); border-radius: 10px;">
    <h2 style="margin-bottom: 1rem; color: var(--bayer-blue);">Ready to Transform Your Document Workflows?</h2>
    <p style="max-width: 700px; margin: 0 auto 2rem; color: #444;">
        Join the growing number of Bayer teams leveraging our Document Intelligence System to streamline operations, 
        improve accuracy, and gain valuable insights from your documents.
    </p>
    <a href="#" class="custom-button" style="margin-right: 10px;">Request Demo</a>
    <a href="#" class="custom-button custom-button-secondary">Contact Us</a>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Bayer_Logo.svg/1200px-Bayer_Logo.svg.png" height="30" style="margin-bottom: 1rem;">
    <p>© 2025 Bayer AG. All rights reserved.</p>
    <p style="margin-top: 0.5rem;">
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Privacy Policy</a> | 
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Terms of Service</a> | 
        <a href="#" style="color: var(--bayer-blue); text-decoration: none; margin: 0 10px;">Contact</a>
    </p>
</div>
""", unsafe_allow_html=True)