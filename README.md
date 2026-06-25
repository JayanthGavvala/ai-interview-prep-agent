#  GradReady — AI Interview Prep for University Students

I built this because I was stressed.

Internship season was coming up and I had no idea how to actually prepare for technical interviews. I'd done the LeetCode grind, read a few articles, watched some YouTube videos — but none of it felt like *real* practice. Nothing was asking me questions about *my* projects, *my* experience, or the specific role I was actually applying for.

So I built something that did.

What started as a personal tool to help me practise turned into a full project I thought could genuinely help other uni students going through the same thing. If you're in first year trying to land your first internship, or a final year student who wants to walk into interviews feeling prepared — this is for you.

---

##  What It Actually Does

You upload your CV, pick the role you're applying for and your year of study, and GradReady generates interview questions based on *your actual experience* — not generic textbook stuff. It reads your CV and asks you about the projects you've listed, the technologies you've used, and the decisions you've made. Just like a real interviewer would.

You can answer by typing or by speaking out loud (which I'd actually recommend — practising out loud is way harder than you think). The AI then gives you honest feedback: what you got right, what you missed, and one concrete thing to work on. It scores you out of 10 and tracks your progress over time so you can see yourself improving.

Everything saves to the cloud, so your history and your score graph are there every time you come back.

---

##  Features

- **CV-aware questions** — upload your PDF and the AI asks about your specific projects and tech stack, not generic questions
- **Role-specific interviews** — choose from 12 internship roles including SWE, Data Science, ML, Product, Cybersecurity, DevOps, and more
- **Year-adjusted difficulty** — 1st year gets foundational questions, 3rd year gets harder industry-level questions
- **Voice or text answers** — speak your answer out loud or type it, your choice
- **Honest AI feedback** — what you got right, what was missing, and one tip to improve
- **Progress tracking** — score history, average, and personal best saved across every session
- **Cloud sync** — log in with a username and your history follows you across devices and sessions
- **Export transcripts** — download your full interview history as a `.txt` file

---

##  Tech Stack

| Layer | Tech |
|---|---|
| Frontend & Backend | Python, Streamlit |
| AI / LLM | Google Gemini 2.5 Flash |
| Database | Google Firebase (Firestore) |
| CV Parsing | PyPDF2 |
| Voice Input | streamlit-mic-recorder |

---

## Running It Locally

### 1. Clone the repo

```bash
git clone https://github.com/jayanthgavvala/ai-interview-prep-agent.git
cd ai-interview-prep-agent
```

### 2. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
# Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your secrets

Create a `.streamlit/secrets.toml` file in the project root:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"

[firebase]
type                        = "service_account"
project_id                  = "your-project-id"
private_key_id              = "your-private-key-id"
private_key                 = "-----BEGIN PRIVATE KEY-----\nYour_Key_Here\n-----END PRIVATE KEY-----\n"
client_email                = "your-client-email"
client_id                   = "your-client-id"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "your-cert-url"
```

> You will need a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) and a Firebase service account key from your [Firebase project settings](https://console.firebase.google.com). See `FIREBASE_SETUP.md` for the full walkthrough.

>  **Never commit `secrets.toml` to GitHub.** Make sure it is in your `.gitignore`.

### 5. Run it

```bash
streamlit run app.py
```

---

##  .gitignore

```gitignore
# Secrets — never commit these
.streamlit/secrets.toml

# Virtual environment
venv/

# Python cache
__pycache__/
*.pyc

# Environment files
.env
*.json
```

---

##  Roadmap

- [ ] PDF export of interview transcripts
- [ ] Global leaderboard to compare scores with other students
- [ ] Behavioural / HR question mode alongside technical questions
- [ ] Company-specific question sets (Google, JP Morgan, etc.)

---

## Why I Made This

Internship applications are brutal, especially when you are at uni and do not have much experience yet. I wanted something that would actually simulate a real interview — one that knew what *I* had worked on and could push me on it. I could not find that, so I built it.

If it helps even one other student walk into an interview feeling more prepared than they would have otherwise, that is enough for me.


