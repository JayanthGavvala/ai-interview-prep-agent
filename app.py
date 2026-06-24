import streamlit as st
import google.generativeai as genai
import google.api_core.exceptions
from streamlit_mic_recorder import speech_to_text
import PyPDF2
import re

# 1. --- Basic App Setup & Apple-Style CSS ---
st.set_page_config(page_title="NexGen Interview AI", page_icon="⚡", layout="centered")

# Injecting Custom CSS for the "Apple" aesthetic
st.markdown("""
    <style>
    /* Use Apple System Fonts and smooth scrolling */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        scroll-behavior: smooth;
    }
    
    /* Hide Streamlit default top header and footer for a clean landing page feel */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hero Title Styling */
    .hero-title {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #FF3366, #FF9933);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: -0.05em;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        line-height: 1.1;
    }
    
    /* Subtitle Styling */
    .hero-subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #888;
        margin-top: 10px;
        margin-bottom: 50px;
        font-weight: 300;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 2rem;
        font-weight: 700;
        margin-top: 60px;
        margin-bottom: 20px;
        letter-spacing: -0.02em;
    }
    </style>
""", unsafe_allow_html=True)

# Configure AI securely
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("API Key not found. Please check your secrets setup.")

# 2. --- State Management ---
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None
if "score_history" not in st.session_state:
    st.session_state.score_history = []
if "cv_context" not in st.session_state:
    st.session_state.cv_context = ""

# ==========================================
# UI SECTION 1: THE HERO BANNER
# ==========================================
st.markdown('<div class="hero-title">NexGen Interview AI</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Pro-level technical interview prep. Powered by Gemini.</div>', unsafe_allow_html=True)

# ==========================================
# UI SECTION 2: CONFIGURATION
# ==========================================
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        role = st.selectbox("Target Role", ["Software Engineer", "Machine Learning Engineer", "Data Scientist"])
    with col2:
        diff = st.select_slider("Difficulty Level", ["Intern", "Junior", "Mid-Level", "Senior"])
        
    st.divider()
    
    uploaded_file = st.file_uploader("Upload your CV to personalize questions (PDF)", type="pdf")
    if uploaded_file:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        st.session_state.cv_context = text
        st.success("CV Processed successfully.")

    # Centered massive generate button
    st.write("") # Spacing
    if st.button("Initialize Interview ⚡", use_container_width=True, type="primary"):
        try:
            with st.spinner("Connecting to Neural Interface..."):
                prompt = f"You are interviewing a {diff} {role}. Ask ONE technical interview question. Keep it concise."
                if st.session_state.cv_context:
                    prompt += f" Look at this CV and ask a question specifically about a project or skill listed here: {st.session_state.cv_context}"
                
                st.session_state.current_question = model.generate_content(prompt).text
                st.session_state.user_answer = None
                st.session_state.feedback = None
        except google.api_core.exceptions.ResourceExhausted:
            st.error("⚠️ AI Rate Limit Reached. Please wait 60 seconds and try again.")


# ==========================================
# UI SECTION 3: THE INTERVIEW ARENA
# ==========================================
if st.session_state.current_question:
    st.markdown('<div class="section-header">Live Interview</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        # 1. AI Question
        with st.chat_message("assistant", avatar="🤖"):
            st.write(st.session_state.current_question)

        # 2. User Answer
        if st.session_state.user_answer:
            with st.chat_message("user", avatar="💻"):
                st.write(st.session_state.user_answer)
                
        # 3. AI Feedback
        if st.session_state.feedback:
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(st.session_state.feedback)
        else:
            # Input mechanisms (only show if no feedback yet)
            st.write("---")
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write("🎙️ **Voice:**")
                spoken = speech_to_text(language='en', start_prompt="Record", stop_prompt="Stop", key='STT')
            with col2:
                st.write("⌨️ **Text:**")
                typed = st.chat_input("Type your response here...")
            
            ans = spoken or typed
            if ans:
                st.session_state.user_answer = ans
                try:
                    with st.spinner("Analyzing parameters..."):
                        eval_prompt = f"""
                        Grade this answer to the question: '{st.session_state.current_question}'. 
                        Candidate said: '{ans}'. 
                        Evaluate them strictly. 
                        CRITICAL: You MUST end your response with a new line exactly like this:
                        FINAL_SCORE: X
                        (Where X is a number from 0 to 10).
                        """
                        feedback_response = model.generate_content(eval_prompt).text
                        st.session_state.feedback = feedback_response
                        
                        # Extract score
                        match = re.search(r"FINAL_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", feedback_response)
                        if match:
                            score = float(match.group(1))
                            st.session_state.score_history.append(score)
                        st.rerun()
                except google.api_core.exceptions.ResourceExhausted:
                    st.error("⚠️ Google API Rate Limit Reached. Please wait 60 seconds before submitting.")

# ==========================================
# UI SECTION 4: PERFORMANCE DASHBOARD
# ==========================================
if len(st.session_state.score_history) > 0:
    st.markdown('<div class="section-header">Performance Metrics</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.metric("Interviews Completed", len(st.session_state.score_history))
    with col2:
        with st.container(border=True):
            avg = sum(st.session_state.score_history) / len(st.session_state.score_history)
            st.metric("Average Score", f"{avg:.1f} / 10.0")
            
    with st.container(border=True):
        st.subheader("Progress Trend")
        st.line_chart(st.session_state.score_history)