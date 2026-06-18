import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import speech_to_text
import PyPDF2 # NEW: Library to read PDF files
import re # NEW: Library to find numbers inside the AI's text

# --- Securely configure the AI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="NexGen Interview AI", page_icon="⚡", layout="wide") # Changed to 'wide' for the dashboard

# --- Custom CSS ---
st.markdown("""
    <style>
    .gradient-text {
        font-size: 42px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px !important;
    }
    .subtitle { color: #888; font-size: 16px; margin-bottom: 30px; }
    </style>
    <div class="gradient-text">NexGen Interview AI</div>
    <div class="subtitle">Powered by Gemini 2.5 ⚡</div>
""", unsafe_allow_html=True)

# --- State Management ---
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None
# NEW: Array to store your scores over time
if "score_history" not in st.session_state:
    st.session_state.score_history = [] 

# --- Sidebar (Settings & PDF Upload) ---
with st.sidebar:
    st.markdown("### 🎛️ Neural Settings")
    role = st.selectbox("Target Role", ["Machine Learning Engineer", "Data Scientist", "Software Engineer"])
    difficulty = st.select_slider("Difficulty Level", options=["Intern", "Junior", "Mid-Level", "Senior"])
    
    st.divider()
    st.markdown("### 📄 Resume Context (Optional)")
    # Streamlit's built-in file uploader component
    uploaded_file = st.file_uploader("Upload your CV to get tailored questions", type="pdf")
    
    cv_text = ""
    if uploaded_file is not None:
        # If a file is uploaded, use PyPDF2 to read all the pages and turn it into text
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            cv_text += page.extract_text()
        st.success("CV Loaded Successfully! 🧠")

    st.divider()
    if st.button("⚡ Generate New Question", use_container_width=True, type="primary"):
        with st.spinner("Initializing neural link..."):
            
            # Base prompt
            question_prompt = f"""
            You are a technical interviewer hiring for a {difficulty} {role} position.
            Generate ONE realistic technical interview question. Do not provide the answer.
            """
            
            # If the user uploaded a CV, append it to the AI's prompt!
            if cv_text:
                question_prompt += f"\n\nHere is the candidate's CV:\n{cv_text}\nMake sure the question specifically tests a skill, project, or technology mentioned in their CV."
                
            response = model.generate_content(question_prompt)
            st.session_state.current_question = response.text
            st.session_state.user_answer = None
            st.session_state.feedback = None

# --- Main Layout: Divide screen into Chat and Dashboard ---
chat_col, dash_col = st.columns([2, 1])

with dash_col:
    st.markdown("### 📈 Performance Dashboard")
    if len(st.session_state.score_history) > 0:
        # Streamlit automatically plots an array of numbers into a line chart!
        st.line_chart(st.session_state.score_history)
        st.metric(label="Average Score", value=f"{sum(st.session_state.score_history)/len(st.session_state.score_history):.1f}/10")
    else:
        st.info("Complete an interview question to see your progress graph!")

with chat_col:
    # --- Main Chat Interface ---
    if st.session_state.current_question is None:
        st.info("👈 Upload your CV (optional) and click **'Generate New Question'** to begin.")
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(st.session_state.current_question)

        if st.session_state.user_answer:
            with st.chat_message("user", avatar="💻"):
                st.write(st.session_state.user_answer)
                
        if st.session_state.feedback:
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(st.session_state.feedback)

    # --- Voice & Text Input Section ---
    if st.session_state.current_question and not st.session_state.feedback:
        st.write("🎙️ **Speak your answer:**")
        spoken_text = speech_to_text(language='en', start_prompt="Click to Start Recording", stop_prompt="🛑 Click to Stop", key='STT')
        typed_text = st.chat_input("...or type your response here")
        
        prompt = spoken_text or typed_text
        
        if prompt:
            st.session_state.user_answer = prompt
            with st.chat_message("user", avatar="💻"):
                st.write(prompt)
                
            with st.chat_message("assistant", avatar="📊"):
                with st.spinner("Analyzing parameters..."):
                    eval_prompt = f"""
                    You are a strict technical interviewer for a {difficulty} {role} position.
                    Question: '{st.session_state.current_question}'
                    Candidate Answer: '{prompt}'
                    
                    Evaluate their answer concisely.
                    CRITICAL: At the very end of your response, you MUST include a score on a new line in this exact format:
                    FINAL_SCORE: X
                    (Where X is a number from 0 to 10).
                    """
                    eval_response = model.generate_content(eval_prompt)
                    feedback_text = eval_response.text
                    
                    st.markdown(feedback_text)
                    st.session_state.feedback = feedback_text
                    
                    # --- Search the AI's text for the "FINAL_SCORE: X" pattern ---
                    score_match = re.search(r"FINAL_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", feedback_text)
                    if score_match:
                        score = float(score_match.group(1))
                        # Save the score to our array so the graph updates!
                        st.session_state.score_history.append(score)
                    
                    st.rerun()