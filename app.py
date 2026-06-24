import streamlit as st
import google.generativeai as genai
import google.api_core.exceptions
from streamlit_mic_recorder import speech_to_text
import PyPDF2
import re
from google.cloud import firestore
from google.oauth2 import service_account


# ──────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG & CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NexGen Interview AI", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        scroll-behavior: smooth;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
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
    .hero-subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #888;
        margin-top: 10px;
        margin-bottom: 50px;
        font-weight: 300;
    }
    .section-header {
        font-size: 2rem;
        font-weight: 700;
        margin-top: 60px;
        margin-bottom: 20px;
        letter-spacing: -0.02em;
    }
    </style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2. AI & FIREBASE INITIALISATION
# ──────────────────────────────────────────────────────────────────────────────
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception:
    st.error("⚠️ Gemini API Key not found. Check your `.streamlit/secrets.toml` file.")
    st.stop()


@st.cache_resource
def get_database():
    """
    Connects to Firestore using credentials stored in secrets.toml.
    Returns a Firestore client, or None if Firebase is not configured.
    """
    if "firebase" not in st.secrets:
        return None
    try:
        creds_dict = dict(st.secrets["firebase"])
        # Firestore requires a Credentials object, not a raw dict.
        # This is the correct way to build it from a service account dict.
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return firestore.Client(
            project=creds_dict["project_id"],
            credentials=credentials,
        )
    except Exception as e:
        st.warning(f"Firebase connection failed: {e}")
        return None


db = get_database()

# ──────────────────────────────────────────────────────────────────────────────
# 3. DATABASE HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def _user_doc_ref(username: str):
    """Returns the Firestore DocumentReference for a given username."""
    return (
        db.collection("artifacts")
        .document("ai-interview-app")
        .collection("users")
        .document(username)
    )


def save_session_to_db(username: str, session_data: dict) -> bool:
    """
    Appends a single interview session to the user's Firestore document.
    Returns True on success, False on failure.
    """
    if not db or not username:
        return False
    try:
        _user_doc_ref(username).set(
            {"history": firestore.ArrayUnion([session_data])},
            merge=True,
        )
        return True
    except Exception as e:
        st.warning(f"Cloud save failed: {e}")
        return False


def load_user_history(username: str) -> list:
    """
    Loads the full interview history for a username from Firestore.
    Returns an empty list if the user doesn't exist yet.
    """
    if not db or not username:
        return []
    try:
        doc = _user_doc_ref(username).get()
        if doc.exists:
            return doc.to_dict().get("history", [])
    except Exception as e:
        st.warning(f"Cloud load failed: {e}")
    return []


# ──────────────────────────────────────────────────────────────────────────────
# 4. SESSION STATE INITIALISATION
# ──────────────────────────────────────────────────────────────────────────────
defaults = {
    "username": "",
    "logged_in": False,          # NEW: explicit login gate
    "current_question": None,
    "user_answer": None,
    "feedback": None,
    "score_history": [],
    "cv_context": "",
    "history_log": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ──────────────────────────────────────────────────────────────────────────────
# 5. HERO BANNER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">NexGen Interview AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Pro-level technical interview prep. Powered by Gemini.</div>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 6. LOGIN / ACCOUNT SECTION
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    with st.container(border=True):
        st.markdown("#### ☁️ Sign In to Sync Your Progress")
        if db is None:
            st.info(
                "Firebase is not configured — progress will only be saved for this session. "
                "Follow `FIREBASE_SETUP.md` to enable cloud persistence."
            )

        col_u, col_btn = st.columns([3, 1])
        with col_u:
            input_username = st.text_input(
                "Username",
                placeholder="Enter a username…",
                label_visibility="collapsed",
            )
        with col_btn:
            login_clicked = st.button("Sign In ➜", use_container_width=True, type="primary")

        if login_clicked:
            if not input_username.strip():
                st.error("Please enter a username.")
            else:
                username = input_username.strip()
                st.session_state.username = username
                st.session_state.logged_in = True

                # ── LOAD PERSISTENT DATA FROM FIREBASE ──────────────────────
                with st.spinner("Loading your cloud profile…"):
                    history = load_user_history(username)

                st.session_state.history_log = history
                # Rebuild the score chart from loaded history
                st.session_state.score_history = [
                    h["score"] for h in history if "score" in h
                ]

                if history:
                    st.success(
                        f"☁️ Welcome back, **{username}**! "
                        f"Loaded {len(history)} previous interview(s)."
                    )
                else:
                    st.success(f"☁️ New profile created for **{username}**. Good luck! 🚀")
                st.rerun()

    # Don't show the rest of the app until the user has signed in
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Signed-in header bar
# ──────────────────────────────────────────────────────────────────────────────
col_info, col_logout = st.columns([4, 1])
with col_info:
    sync_label = "☁️ Cloud Sync ON" if db else "💾 Local Session Only"
    st.caption(f"Signed in as **{st.session_state.username}** · {sync_label}")
with col_logout:
    if st.button("Sign Out", use_container_width=True):
        for key in defaults:
            st.session_state[key] = defaults[key]
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 7. CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        role = st.selectbox(
            "Target Role",
            ["Software Engineer", "Machine Learning Engineer", "Data Scientist"],
        )
    with col2:
        diff = st.select_slider(
            "Difficulty Level", ["Intern", "Junior", "Mid-Level", "Senior"]
        )

    st.divider()

    uploaded_file = st.file_uploader(
        "Upload your CV to personalise questions (PDF)", type="pdf"
    )
    if uploaded_file:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        cv_text = ""
        for page in pdf_reader.pages:
            cv_text += page.extract_text() or ""
        st.session_state.cv_context = cv_text
        st.success("✅ CV processed — questions will be tailored to your experience.")

    st.write("")
    if st.button("Initialize Interview ⚡", use_container_width=True, type="primary"):
        try:
            with st.spinner("Connecting to Neural Interface…"):
                prompt = (
                    f"You are interviewing a {diff} {role}. "
                    "Ask ONE concise, specific technical interview question."
                )
                if st.session_state.cv_context:
                    prompt += (
                        " The candidate's CV is provided below. "
                        "Ask a question that digs into a specific project, technology, or "
                        "decision they made — as a Senior Engineer would in a real interview.\n\n"
                        f"CV:\n{st.session_state.cv_context}"
                    )
                st.session_state.current_question = model.generate_content(prompt).text
                st.session_state.user_answer = None
                st.session_state.feedback = None
        except google.api_core.exceptions.ResourceExhausted:
            st.error("⚠️ AI Rate Limit reached. Wait 60 seconds and try again.")

# ──────────────────────────────────────────────────────────────────────────────
# 8. LIVE INTERVIEW ARENA
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.current_question:
    st.markdown('<div class="section-header">Live Interview</div>', unsafe_allow_html=True)

    with st.container(border=True):
        with st.chat_message("assistant", avatar="🤖"):
            st.write(st.session_state.current_question)

        if st.session_state.user_answer:
            with st.chat_message("user", avatar="💻"):
                st.write(st.session_state.user_answer)

        if st.session_state.feedback:
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(st.session_state.feedback)
        else:
            st.write("---")
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write("🎙️ **Voice:**")
                spoken = speech_to_text(
                    language="en",
                    start_prompt="Record",
                    stop_prompt="Stop",
                    key="STT",
                )
            with col2:
                st.write("⌨️ **Text:**")
                typed = st.chat_input("Type your response here…")

            ans = spoken or typed
            if ans:
                st.session_state.user_answer = ans
                try:
                    with st.spinner("Analysing your answer…"):
                        eval_prompt = f"""
You are a strict but fair Senior Engineer conducting a technical interview.

Question asked: '{st.session_state.current_question}'
Candidate's answer: '{ans}'

Evaluate the answer. Call out:
- What they got right
- What key concepts or depth was missing
- Any inaccuracies

CRITICAL: End your response with EXACTLY this line (no extra text after it):
FINAL_SCORE: X
(where X is a whole number from 0 to 10)
"""
                        feedback_text = model.generate_content(eval_prompt).text
                        st.session_state.feedback = feedback_text

                        # Extract numeric score
                        match = re.search(
                            r"FINAL_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", feedback_text
                        )
                        score_val = float(match.group(1)) if match else 0.0
                        st.session_state.score_history.append(score_val)

                        session_data = {
                            "question": st.session_state.current_question,
                            "answer": ans,
                            "feedback": feedback_text,
                            "score": score_val,
                        }
                        st.session_state.history_log.append(session_data)

                        # ── PERSIST TO FIREBASE ──────────────────────────────
                        if st.session_state.username:
                            saved = save_session_to_db(
                                st.session_state.username, session_data
                            )
                            # Silent save — no success toast needed in the flow

                        st.rerun()
                except google.api_core.exceptions.ResourceExhausted:
                    st.error(
                        "⚠️ Google API Rate Limit reached. Wait 60 seconds before submitting."
                    )

# ──────────────────────────────────────────────────────────────────────────────
# 9. PERFORMANCE DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.score_history:
    st.markdown(
        '<div class="section-header">Performance Metrics</div>', unsafe_allow_html=True
    )

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

# ──────────────────────────────────────────────────────────────────────────────
# 10. ARCHIVED TRANSCRIPTS & EXPORT
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.history_log:
    st.markdown(
        '<div class="section-header">Response Logs & Export</div>', unsafe_allow_html=True
    )

    report_lines = ["NEXGEN INTERVIEW AI REPORT", "=" * 60, ""]
    for i, log in enumerate(st.session_state.history_log, start=1):
        report_lines += [
            f"SESSION {i} | SCORE: {log.get('score', 'N/A')}/10",
            f"Question:  {log['question'].strip()}",
            f"Answer:    {log['answer'].strip()}",
            f"Feedback:\n{log['feedback'].strip()}",
            "-" * 50,
            "",
        ]
    report_text = "\n".join(report_lines)

    col_dl, _ = st.columns([1, 2])
    with col_dl:
        st.download_button(
            label="📥 Export Full Transcripts (.txt)",
            data=report_text,
            file_name="nexgen_interview_transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.write("")

    for idx, log in enumerate(reversed(st.session_state.history_log)):
        real_index = len(st.session_state.history_log) - idx
        with st.expander(
            f"📝 Session {real_index}: {log['question'][:55]}… (Score: {log.get('score', '?')}/10)"
        ):
            st.markdown(f"**Interviewer:**\n{log['question']}")
            st.markdown(f"**Your Answer:**\n*{log['answer']}*")
            st.markdown(f"**Evaluation:**\n{log['feedback']}")