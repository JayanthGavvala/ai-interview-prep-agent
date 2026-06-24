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
st.set_page_config(page_title="GradReady — AI Interview Prep", page_icon="🎓", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        scroll-behavior: smooth;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Hero ── */
    .hero-wrap {
        text-align: center;
        padding: 48px 0 12px 0;
    }
    .hero-eyebrow {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #7C3AED;
        background: #EDE9FE;
        border-radius: 99px;
        padding: 4px 14px;
        margin-bottom: 20px;
    }
    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        line-height: 1.08;
        letter-spacing: -0.04em;
        color: #FFFFFF; 
        margin-bottom: 0;
    }
    .hero-title span {
        background: linear-gradient(135deg, #EF4444 0%, #F97316 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #6B7280;
        margin-top: 14px;
        font-weight: 400;
        line-height: 1.6;
    }

    /* ── Section labels ── */
    .section-header {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 52px;
        margin-bottom: 16px;
        letter-spacing: -0.03em;
        color: #EF4444;  /* ← change this */
    }

    /* ── Year badge pills ── */
    .year-desc {
        font-size: 0.78rem;
        color: #6B7280;
        margin-top: 2px;
    }

    /* ── Stat cards ── */
    [data-testid="stMetric"] {
        background: #F9F7FF;
        border: 1px solid #EDE9FE;
        border-radius: 12px;
        padding: 16px 20px !important;
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
    if "firebase" not in st.secrets:
        return None
    try:
        creds_dict = dict(st.secrets["firebase"])
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return firestore.Client(project=creds_dict["project_id"], credentials=credentials)
    except Exception as e:
        st.warning(f"Firebase connection failed: {e}")
        return None


db = get_database()

# ──────────────────────────────────────────────────────────────────────────────
# 3. DATABASE HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def _user_doc_ref(username: str):
    return (
        db.collection("artifacts")
        .document("gradready-app")
        .collection("users")
        .document(username)
    )

def save_session_to_db(username: str, session_data: dict) -> bool:
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
# 4. CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
ROLES = [
    "Software Engineering Intern",
    "Data Science Intern",
    "Machine Learning Intern",
    "Product Management Intern",
    "Cybersecurity Intern",
    "DevOps / Cloud Intern",
    "Frontend Developer Intern",
    "Backend Developer Intern",
    "AI / Research Intern",
    "Business Analyst Intern",
    "UX / Product Design Intern",
    "Quantitative Analyst Intern",
]

YEAR_OPTIONS = {
    "1st Year": {
        "label": "1st Year",
        "desc": "Foundational concepts, no internship experience yet",
        "interviewer_note": (
            "The candidate is a first-year university student with limited experience. "
            "Ask beginner-friendly but still real technical questions. "
            "Focus on fundamentals, reasoning ability, and eagerness to learn."
        ),
    },
    "2nd Year": {
        "label": "2nd Year",
        "desc": "Some coursework projects, possibly a first placement",
        "interviewer_note": (
            "The candidate is a second-year university student who has completed core modules "
            "and may have personal or coursework projects. "
            "Ask mid-level questions that probe understanding beyond the surface."
        ),
    },
    "3rd Year": {
        "label": "3rd Year",
        "desc": "Final year / placement year, strong project portfolio",
        "interviewer_note": (
            "The candidate is a final-year or placement-year student expected to hit the ground running. "
            "Ask challenging, industry-level questions. Probe depth, trade-offs, and real-world thinking."
        ),
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# 5. SESSION STATE
# ──────────────────────────────────────────────────────────────────────────────
defaults = {
    "username": "",
    "logged_in": False,
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
# 6. HERO BANNER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-eyebrow">🎓 Built for University Students</div>
    <div class="hero-title">Land Your<br><span>Internship</span></div>
    <div class="hero-subtitle">
        AI-powered mock interviews tailored to your year, your role, and your CV.<br>
        Practice like it's real. Walk in ready.
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

# ──────────────────────────────────────────────────────────────────────────────
# 7. LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    with st.container(border=True):
        st.markdown("#### Sign in to save your progress")
        if db is None:
            st.info("☁️ Firebase not configured — progress saves for this session only.")

        col_u, col_btn = st.columns([3, 1])
        with col_u:
            input_username = st.text_input(
                "Username",
                placeholder="Pick a username to track your progress…",
                label_visibility="collapsed",
            )
        with col_btn:
            login_clicked = st.button("Let's go →", use_container_width=True, type="primary")

        if login_clicked:
            if not input_username.strip():
                st.error("Please enter a username.")
            else:
                username = input_username.strip()
                st.session_state.username = username
                st.session_state.logged_in = True
                with st.spinner("Loading your profile…"):
                    history = load_user_history(username)
                st.session_state.history_log = history
                st.session_state.score_history = [h["score"] for h in history if "score" in h]
                if history:
                    st.success(f"Welcome back, **{username}**! {len(history)} session(s) loaded. 🎉")
                else:
                    st.success(f"Profile created for **{username}**. Time to practise! 🚀")
                st.rerun()
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Signed-in bar
# ──────────────────────────────────────────────────────────────────────────────
col_info, col_logout = st.columns([4, 1])
with col_info:
    sync_label = "☁️ Progress syncing" if db else "💾 Session only"
    st.caption(f"Signed in as **{st.session_state.username}** · {sync_label}")
with col_logout:
    if st.button("Sign out", use_container_width=True):
        for key in defaults:
            st.session_state[key] = defaults[key]
        st.rerun()

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# 8. INTERVIEW SETUP
# ──────────────────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("#### 🎯 Set Up Your Mock Interview")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**What role are you applying for?**")
        role = st.selectbox(
            "Role",
            ROLES,
            label_visibility="collapsed",
            help="Choose the internship role you're targeting",
        )
    with col2:
        st.markdown("**What year are you in?**")
        year_choice = st.radio(
            "Year",
            options=list(YEAR_OPTIONS.keys()),
            label_visibility="collapsed",
            horizontal=True,
        )
        st.markdown(f'<div class="year-desc">{YEAR_OPTIONS[year_choice]["desc"]}</div>', unsafe_allow_html=True)

    st.divider()

    uploaded_file = st.file_uploader(
        "📄 Upload your CV for personalised questions (optional, PDF)",
        type="pdf",
    )
    if uploaded_file:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        cv_text = ""
        for page in pdf_reader.pages:
            cv_text += page.extract_text() or ""
        st.session_state.cv_context = cv_text
        st.success("✅ CV uploaded — questions will be tailored to your projects and experience.")

    st.write("")
    if st.button("Start Interview ⚡", use_container_width=True, type="primary"):
        try:
            with st.spinner("Generating your question…"):
                year_note = YEAR_OPTIONS[year_choice]["interviewer_note"]

                prompt = (
                    f"You are a Senior Engineer at a top tech company interviewing a university student "
                    f"for a **{role}** position.\n\n"
                    f"{year_note}\n\n"
                    "Ask ONE specific, realistic internship interview question. "
                    "Keep it concise — one question only, no preamble."
                )

                if st.session_state.cv_context:
                    prompt += (
                        "\n\nThe student has uploaded their CV. Read it and ask a question "
                        "that probes a specific project, technology, or decision they mention — "
                        "exactly as a real interviewer would.\n\n"
                        f"CV:\n{st.session_state.cv_context}"
                    )

                st.session_state.current_question = model.generate_content(prompt).text
                st.session_state.user_answer = None
                st.session_state.feedback = None
        except google.api_core.exceptions.ResourceExhausted:
            st.error("⚠️ AI rate limit hit. Wait 60 seconds and try again.")

# ──────────────────────────────────────────────────────────────────────────────
# 9. LIVE INTERVIEW
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.current_question:
    st.markdown('<div class="section-header">🎤 Your Interview</div>', unsafe_allow_html=True)

    with st.container(border=True):
        with st.chat_message("assistant", avatar="🤖"):
            st.write(st.session_state.current_question)

        if st.session_state.user_answer:
            with st.chat_message("user", avatar="🎓"):
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
                typed = st.chat_input("Type your answer here…")

            ans = spoken or typed
            if ans:
                st.session_state.user_answer = ans
                try:
                    with st.spinner("Evaluating your answer…"):
                        eval_prompt = f"""
You are a Senior Engineer evaluating a university student's answer in a mock internship interview.

Role they're applying for: {role}
Student year: {year_choice}
Question asked: '{st.session_state.current_question}'
Student's answer: '{ans}'

Give honest, constructive feedback a real interviewer would give. Cover:
- ✅ What they got right
- ❌ What was missing or could be stronger
- 💡 One concrete tip to improve their answer

Be encouraging but don't sugarcoat gaps — students need real feedback to improve.

CRITICAL: End your response with EXACTLY this line (nothing after it):
FINAL_SCORE: X
(where X is a whole number from 0 to 10)
"""
                        feedback_text = model.generate_content(eval_prompt).text
                        st.session_state.feedback = feedback_text

                        match = re.search(r"FINAL_SCORE:\s*([0-9]+(?:\.[0-9]+)?)", feedback_text)
                        score_val = float(match.group(1)) if match else 0.0
                        st.session_state.score_history.append(score_val)

                        session_data = {
                            "question": st.session_state.current_question,
                            "answer": ans,
                            "feedback": feedback_text,
                            "score": score_val,
                            "role": role,
                            "year": year_choice,
                        }
                        st.session_state.history_log.append(session_data)

                        if st.session_state.username:
                            save_session_to_db(st.session_state.username, session_data)

                        st.rerun()
                except google.api_core.exceptions.ResourceExhausted:
                    st.error("⚠️ Rate limit hit. Wait 60 seconds before submitting.")

# ──────────────────────────────────────────────────────────────────────────────
# 10. PERFORMANCE DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.score_history:
    st.markdown('<div class="section-header">📈 Your Progress</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("Sessions Done", len(st.session_state.score_history))
    with col2:
        with st.container(border=True):
            avg = sum(st.session_state.score_history) / len(st.session_state.score_history)
            st.metric("Average Score", f"{avg:.1f} / 10")
    with col3:
        with st.container(border=True):
            best = max(st.session_state.score_history)
            st.metric("Personal Best", f"{best:.0f} / 10")

    with st.container(border=True):
        st.subheader("Score trend")
        st.line_chart(st.session_state.score_history)

# ──────────────────────────────────────────────────────────────────────────────
# 11. TRANSCRIPT LOG & EXPORT
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.history_log:
    st.markdown('<div class="section-header">📝 Past Sessions</div>', unsafe_allow_html=True)

    report_lines = ["GRADREADY — INTERVIEW TRANSCRIPT", "=" * 60, ""]
    for i, log in enumerate(st.session_state.history_log, start=1):
        report_lines += [
            f"SESSION {i} | {log.get('role', 'N/A')} | {log.get('year', 'N/A')} | SCORE: {log.get('score', 'N/A')}/10",
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
            label="📥 Export Transcripts (.txt)",
            data=report_text,
            file_name="gradready_transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.write("")

    for idx, log in enumerate(reversed(st.session_state.history_log)):
        real_index = len(st.session_state.history_log) - idx
        role_tag = log.get("role", "")
        year_tag = log.get("year", "")
        with st.expander(
            f"Session {real_index} · {role_tag} · {year_tag} · Score: {log.get('score', '?')}/10"
        ):
            st.markdown(f"**Question:**\n{log['question']}")
            st.markdown(f"**Your Answer:**\n*{log['answer']}*")
            st.markdown(f"**Feedback:**\n{log['feedback']}")