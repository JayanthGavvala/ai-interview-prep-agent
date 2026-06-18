import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import speech_to_text
import PyPDF2
import re

# 1. --- Basic App Setup ---
st.set_page_config(page_title="NexGen Interview AI", page_icon="⚡", layout="wide")

# Custom CSS for slick UI
st.markdown("""
    <style>
    .gradient-text { font-size: 42px !important; font-weight: 800 !important; 
                     background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe, #00f2fe);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0px !important;}
    </style>
""", unsafe_allow_html=True)

# Configure AI securely
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("API Key not found or invalid. Please check your secrets setup.")

# 2. --- State Management (The Mock Database) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
# This dictionary acts as our temporary database storing users and their scores
if "user_database" not in st.session_state:
    st.session_state.user_database = {} 
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# 3. --- Page Components (Functions) ---

def login_screen():
    """Handles the Authentication UI"""
    st.markdown('<div class="gradient-text">NexGen Interview AI</div>', unsafe_allow_html=True)
    st.write("Welcome back. Please log in to access your interview dashboard.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔐 System Login")
            login_user = st.text_input("Username")
            login_pass = st.text_input("Password", type="password") # Visual only for now
            
            if st.button("Login", use_container_width=True, type="primary"):
                if login_user:
                    # In a real app, we check the database here. For now, we let anyone in!
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    
                    # Create a profile for them if they are new
                    if login_user not in st.session_state.user_database:
                        st.session_state.user_database[login_user] = {"scores": [], "cv_uploaded": False}
                    
                    st.rerun() # Refresh page to hide login screen
                else:
                    st.error("Please enter a username.")

def interview_room():
    """The main AI Interview simulator"""
    st.header(f"🎙️ Interview Room")
    st.write("Configure your settings and begin the simulation.")
    
    chat_col, set_col = st.columns([2, 1])
    
    with set_col:
        with st.container(border=True):
            st.markdown("### 🎛️ Parameters")
            role = st.selectbox("Role", ["Machine Learning Engineer", "Software Engineer", "Data Scientist"])
            diff = st.select_slider("Difficulty", ["Intern", "Junior", "Mid-Level"])
            
            uploaded_file = st.file_uploader("Attach CV (Optional)", type="pdf")
            cv_text = ""
            if uploaded_file:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    cv_text += page.extract_text()
                st.session_state.user_database[st.session_state.username]["cv_uploaded"] = True
                st.success("CV Processed")
                
            if st.button("⚡ Generate Question", use_container_width=True, type="primary"):
                with st.spinner("Connecting to AI..."):
                    prompt = f"You are interviewing a {diff} {role}. Ask one technical question. Keep it concise."
                    if cv_text:
                        prompt += f" Ask a highly specific question based on this candidate's CV: {cv_text}"
                    
                    st.session_state.current_question = model.generate_content(prompt).text
                    st.session_state.user_answer = None
                    st.session_state.feedback = None

    with chat_col:
        with st.container(border=True):
            if not st.session_state.current_question:
                st.info("Awaiting simulation start... Click 'Generate Question' on the right.")
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(st.session_state.current_question)

                if st.session_state.user_answer:
                    with st.chat_message("user", avatar="💻"):
                        st.write(st.session_state.user_answer)
                        
                if st.session_state.feedback:
                    with st.chat_message("assistant", avatar="📊"):
                        st.markdown(st.session_state.feedback)
                else:
                    st.write("🎙️ **Speak your answer:**")
                    spoken = speech_to_text(language='en', start_prompt="Start Recording", stop_prompt="Stop Recording", key='STT')
                    typed = st.chat_input("Or type your response here...")
                    
                    ans = spoken or typed
                    if ans:
                        st.session_state.user_answer = ans
                        with st.spinner("Analyzing parameters..."):
                            eval_prompt = f"""
                            Grade this answer to the question: '{st.session_state.current_question}'. 
                            Candidate said: '{ans}'. 
                            Evaluate them as a strict interviewer.
                            CRITICAL: You MUST end your response with a new line exactly like this:
                            FINAL_SCORE: X
                            (Where X is a number from 0 to 10).
                            """
                            feedback = model.generate_content(eval_prompt).text
                            st.session_state.feedback = feedback
                            
                            # Extract score and save to user's database profile!
                            match = re.search(r"FINAL_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", feedback)
                            if match:
                                # Save the score for the specific user logged in
                                st.session_state.user_database[st.session_state.username]["scores"].append(float(match.group(1)))
                            st.rerun()

def profile_dashboard():
    """Shows user statistics"""
    st.header(f"📊 {st.session_state.username}'s Profile")
    user_data = st.session_state.user_database[st.session_state.username]
    scores = user_data["scores"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Mock Interviews Completed", len(scores))
    with col2:
        avg = sum(scores)/len(scores) if scores else 0
        st.metric("Average Score", f"{avg:.1f} / 10")
        
    st.divider()
    if len(scores) > 0:
        st.subheader("Performance Trend")
        st.line_chart(scores)
    else:
        st.info("Complete an interview to generate your performance graph.")

def settings_page():
    """Settings and Logout"""
    st.header("⚙️ Account Settings")
    st.write(f"Currently logged in as: **{st.session_state.username}**")
    st.divider()
    st.error("Danger Zone")
    if st.button("Log Out", type="secondary"):
        # Reset everything on logout
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.current_question = None
        st.session_state.user_answer = None
        st.session_state.feedback = None
        st.rerun()

# 4. --- Main App Router ---
# This acts like the "traffic controller" for your app
if not st.session_state.logged_in:
    login_screen()
else:
    # Sidebar Navigation Menu
    with st.sidebar:
        st.markdown('<div class="gradient-text" style="font-size: 24px !important;">NexGen AI</div>', unsafe_allow_html=True)
        st.write(f"👤 {st.session_state.username}")
        st.divider()
        # Radio buttons act as our page links
        page = st.radio("Navigation", ["🎙️ Interview Room", "📊 Profile & Stats", "⚙️ Settings"])
    
    # Route to the correct page function based on what the user clicked
    if page == "🎙️ Interview Room":
        interview_room()
    elif page == "📊 Profile & Stats":
        profile_dashboard()
    elif page == "⚙️ Settings":
        settings_page()