import streamlit as st
import google.generativeai as genai

# --- Securely configure the AI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# Set layout to 'centered' for a cleaner look
st.set_page_config(page_title="Interview AI", page_icon="⚡", layout="centered")

# --- Custom CSS for a Cool Glowing Title ---
st.markdown("""
    <style>
    .gradient-text {
        font-size: 42px !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #00f2fe, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .subtitle {
        color: #888;
        font-size: 16px;
        margin-bottom: 30px;
    }
    </style>
    <div class="gradient-text">NexGen Interview AI</div>
    <div class="subtitle">Powered by Gemini 2.5 ⚡</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🎛️ Neural Settings")
    role = st.selectbox("Target Role", ["Machine Learning Engineer", "Data Scientist", "Software Engineer"])
    difficulty = st.select_slider("Difficulty Level", options=["Intern", "Junior", "Mid-Level", "Senior"])
    st.divider()
    
    # We use a button in the sidebar to reset the interview
    if st.button("⚡ Generate New Question", use_container_width=True, type="primary"):
        with st.spinner("Initializing neural link..."):
            question_prompt = f"""
            You are a technical interviewer hiring for a {difficulty} {role} position.
            Generate ONE realistic technical interview question. 
            Do not provide the answer, just the question. Keep it concise.
            """
            response = model.generate_content(question_prompt)
            
            # Reset the memory for a new question
            st.session_state.current_question = response.text
            st.session_state.user_answer = None
            st.session_state.feedback = None

# --- State Management ---
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = None
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# --- Main Chat Interface ---
if st.session_state.current_question is None:
    # Empty state before they click the button
    st.info("👈 Configure your settings in the sidebar and click **'Generate New Question'** to begin the simulation.")
else:
    # 1. Show the Interviewer's Question
    with st.chat_message("assistant", avatar="🤖"):
        st.write(st.session_state.current_question)

    # 2. Show the User's Answer (if they submitted one)
    if st.session_state.user_answer:
        with st.chat_message("user", avatar="💻"):
            st.write(st.session_state.user_answer)
            
    # 3. Show the AI's Feedback (if it exists)
    if st.session_state.feedback:
        with st.chat_message("assistant", avatar="📊"):
            st.markdown(st.session_state.feedback)

# --- Floating Chat Input (Anchors to the bottom of the screen) ---
# We only show this if a question has been asked, but NO feedback has been given yet
if st.session_state.current_question and not st.session_state.feedback:
    prompt = st.chat_input("Type your response to the interviewer...")
    
    if prompt:
        # Save the user's answer
        st.session_state.user_answer = prompt
        
        # Immediately display it on screen
        with st.chat_message("user", avatar="💻"):
            st.write(prompt)
            
        # Generate and display the feedback
        with st.chat_message("assistant", avatar="📊"):
            with st.spinner("Analyzing parameters..."):
                eval_prompt = f"""
                You are a strict but fair technical interviewer for a {difficulty} {role} position.
                The interview question was: '{st.session_state.current_question}'
                The candidate answered: '{prompt}'
                
                Please evaluate their answer. Point out what they got right, what they missed or got wrong, 
                and give them a score out of 10. Keep your feedback concise and professional.
                """
                eval_response = model.generate_content(eval_prompt)
                
                st.markdown(eval_response.text)
                # Save the feedback to memory so it stays on screen after a refresh
                st.session_state.feedback = eval_response.text
                
                # Small visual flair
                st.toast('Analysis Complete!', icon='✅') 