# ⚡ NexGen AI Interview Simulator

> An AI-powered interview prep tool that reads your CV and grills you on your *actual* experience — just like a real Senior Engineer would.

Instead of generic LeetCode drills, NexGen parses your uploaded CV and generates highly specific, contextual technical questions based on your real past projects and listed experience.

---

## ✨ Features

- **Context-Aware Interviewing** — Extracts text from your uploaded CV via `PyPDF2` and injects your real experience into the LLM's system prompt, generating questions tailored specifically to *you*.
- **Multi-Modal Responses** — Practice answering out loud with browser-based Speech-to-Text (`streamlit-mic-recorder`), or fall back to standard text input.
- **Instant AI Feedback** — Powered by Google Gemini 2.5 Flash, acting as a strict technical interviewer: evaluating accuracy, surfacing missing concepts, and grading each answer out of 10.
- **Cloud Progress Tracking** — Google Firebase (Firestore) stores your profile, full interview transcripts, and historical performance trends on a live dashboard.
- **Modern UI/UX** — Streamlit with custom-injected CSS for a sleek, single-page interface that feels native to modern SaaS platforms.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Python, Streamlit, HTML/CSS (custom styling) |
| Backend | Google Firebase (Firestore) |
| AI / LLM | Google Generative AI (Gemini 2.5 Flash) |
| Utilities | PyPDF2, streamlit-mic-recorder, RegEx |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/jayanthgavvala/ai-interview-prep-agent.git
cd ai-interview-prep-agent
```

### 2. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment secrets

Create a `.streamlit/` folder in the project root, then add a `secrets.toml` file inside it:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"

[firebase]
type                        = "service_account"
project_id                  = "your_project_id"
private_key_id              = "your_private_key_id"
private_key                 = "-----BEGIN PRIVATE KEY-----\nYour_Key_Here\n-----END PRIVATE KEY-----\n"
client_email                = "your_client_email"
client_id                   = "your_client_id"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "your_cert_url"
```

> **⚠️ Security:** Never commit `secrets.toml` to version control.  
> Make sure `.streamlit/secrets.toml` is listed in your `.gitignore` (see below).

### 5. Launch the app

```bash
streamlit run app.py
```

---

## 🔒 `.gitignore` (recommended)

Ensure the following entries are present to keep secrets and environment files out of your repository:

```gitignore
# Secrets
.streamlit/secrets.toml

# Python virtual environment
venv/
.env

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# OS artefacts
.DS_Store
Thumbs.db
```

---

## 📈 Roadmap

- [ ] **Export Transcripts** — Download PDF reports of past interview sessions.
- [ ] **Global Leaderboard** — Compare your average scores against other candidates.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

