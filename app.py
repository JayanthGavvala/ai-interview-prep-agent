import streamlit as st
import google.generativeai as genai
import google.api_core.exceptions
from streamlit_mic_recorder import speech_to_text
import PyPDF2
import re
from google.cloud import firestore # NEW: Cloud Database Import

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

# --- Initialize Firebase Database ---
@st.cache_resource
def get_database():
    if "firebase" in st.secrets:
        creds_dict = dict(st.secrets["firebase"])
        return firestore.Client.from_service_account_info(creds_dict)
    return None

db = get_database()

def save_session_to_db(username, session_data):
    if db and username:
        # We use ArrayUnion to safely append new interviews to your permanent history
        doc_ref = db.collection('artifacts').document('ai-interview-app').collection('users').document(username)
        doc_ref.set({"history": firestore.ArrayUnion([session_data])}, merge=True)
        
def load_user_history(username):
    if db and username:
        doc = db.collection('artifacts').document('ai-interview-app').collection('users').document(username).get()
        if doc.exists:
            return doc.to_dict().get("history", [])
    return []

# 2. --- State Management ---
if "username" not in st.session_state:
    st.session_state.username = ""
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
# NEW: List to save session history log of previous responses
if "history_log" not in st.session_state:
    st.session_state.history_log = []

# ==========================================
# UI SECTION 1: THE HERO BANNER
# ==========================================
st.markdown('<div class="hero-title">NexGen Interview AI</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Pro-level technical interview prep. Powered by Gemini.</div>', unsafe_allow_html=True)

# NEW: Sleek Cloud Sync Input (Acts like a login without the clunky page)
user_id = st.text_input("Cloud Sync ID", placeholder="Enter a username to permanently sync progress to the cloud...", label_visibility="collapsed")
if user_id and user_id != st.session_state.username:
    st.session_state.username = user_id
    # Load history from the cloud
    st.session_state.history_log = load_user_history(user_id)
    # Rebuild the line chart from the loaded history
    st.session_state.score_history = [log["score"] for log in st.session_state.history_log]
    if st.session_state.history_log:
        st.success(f"☁️ Cloud profile loaded for **{user_id}**. Welcome back!")
    else:
        st.success(f"☁️ New cloud profile created for **{user_id}**.")

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
                        score_val = 0.0
                        if match:
                            score_val = float(match.group(1))
                            st.session_state.score_history.append(score_val)
                        
                        # Save session log internally
                        session_data = {
                            "question": st.session_state.current_question,
                            "answer": ans,
                            "feedback": feedback_response,
                            "score": score_val
                        }
                        st.session_state.history_log.append(session_data)
                        
                        # Push to Firebase if the user entered a Cloud Sync ID
                        if st.session_state.username:
                            save_session_to_db(st.session_state.username, session_data)
                            
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

# ==========================================
# UI SECTION 5: ARCHIVED INTERVIEW TRANSCRIPTS & EXPORT
# ==========================================
if len(st.session_state.history_log) > 0:
    st.markdown('<div class="section-header">Response Logs & Export</div>', unsafe_allow_html=True)
    
    # Generate the structured text file to allow downloading locally
    report_text = "NEXGEN INTERVIEW AI REPORT\n============================\n\n"
    for i, log in enumerate(st.session_state.history_log):
        report_text += f"SESSION {i + 1} | SCORE: {log['score']}/10\n"
        report_text += f"Question: {log['question'].strip()}\n"
        report_text += f"Your Response: {log['answer'].strip()}\n"
        report_text += f"Evaluation:\n{log['feedback'].strip()}\n"
        report_text += "-" * 50 + "\n\n"
        
    # Apple-style download component layout
    col_dl, col_space = st.columns([1, 2])
    with col_dl:
        st.download_button(
            label="📥 Export Full Transcripts (.txt)",
            data=report_text,
            file_name="nexgen_interview_prep_transcript.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    st.write("") # Spacing
    
    # Loop backwards through history so the most recent question is at the top
    for idx, log in enumerate(reversed(st.session_state.history_log)):
        real_index = len(st.session_state.history_log) - idx
        with st.expander(f"📝 Session {real_index}: {log['question'][:55]}... (Score: {log['score']}/10)"):
            st.markdown(f"**Interviewer:**\n{log['question']}")
            st.markdown(f"**Your Answer:**\n*{log['answer']}*")
            st.markdown(f"**Interviewer Evaluation:**\n{log['feedback']}")