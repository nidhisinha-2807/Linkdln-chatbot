# 💼 LinkedIn Profile Optimizer

An AI-powered career coaching app that analyzes your LinkedIn profile, scores it, rewrites sections, checks job fit, and builds a personalized career roadmap — all in a conversational chat interface.

---

## 🚀 Live Demo

> **[Add your Streamlit Cloud / hosted URL here]**

---

## ✨ Features

- **Profile Scoring** — Get a structured score across headline, about section, experience, skills, and completeness
- **AI Headline & About Rewriter** — Rewrites your LinkedIn sections for your target role using Llama 3.3 70B
- **Job Fit Analysis** — Paste any job description and get a match score, skill gap analysis, and tailored advice
- **Career Roadmap** — Personalized learning path and skill recommendations based on your goals
- **Memory-aware Chat** — The assistant remembers your profile, goals, and conversation context across turns
- **3 Input Methods** — LinkedIn URL (via Apify), LinkedIn PDF export, or Demo profile

---

## 🧠 Architecture

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                    │
│  Sidebar (Profile Loader) + Chat Interface       │
└────────────────────┬────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │     Orchestrator     │  ← routes user intent
          │   (LangGraph Agent)  │
          └──────────┬──────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Profile        Job Fit      Career
   Analyzer       Checker      Advisor
        │            │            │
        └────────────┴────────────┘
                     │
          ┌──────────▼──────────┐
          │   Groq API           │
          │   Llama 3.3 70B      │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   Memory Manager     │  ← session state, profile, goals
          └─────────────────────┘
```

**Data Flow:**
1. User loads profile (URL → Apify scraper → normalize, or PDF → pdfplumber parser, or Demo)
2. Orchestrator classifies the user's intent (analyze / rewrite / job fit / career advice)
3. Relevant agent builds a prompt with profile context + conversation history
4. Groq (Llama 3.3 70B) generates the response
5. Memory Manager stores goals, analyzed jobs, and message history for context continuity

---

## 🗂️ Project Structure

```
linkedin-optimizer/
├── app.py                    # Streamlit entry point, UI layout
├── agents/
│   └── orchestrator.py       # LangGraph agent, intent routing
├── tools/
│   └── linkedin_scraper.py   # Apify URL scraping + PDF parsing + demo profile
├── memory/
│   └── memory_manager.py     # Session state, profile storage, message history
├── utils/
│   └── helpers.py            # Greeting messages, profile loaded messages
├── .env                      # API keys (not committed)
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/linkedin-optimizer.git
cd linkedin-optimizer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up API keys

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
APIFY_API_TOKEN=your_apify_token_here   # optional, needed for URL scraping
```

- **Groq API key** (free): [console.groq.com](https://console.groq.com)
- **Apify token** (free $5 credits): [console.apify.com](https://console.apify.com/account/integrations)

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📋 Requirements

```
streamlit
groq
langgraph
langchain
apify-client
pdfplumber
python-dotenv
```

See `requirements.txt` for pinned versions.

---

## 📥 Loading Your LinkedIn Profile

### Option A: LinkedIn URL (via Apify)
Paste your `linkedin.com/in/yourname` URL in the sidebar. Uses the `anchor/linkedin-profile-enrichment` actor (~$0.01/profile from your free $5 credits).

### Option B: LinkedIn PDF Export (Free, No API)
1. Go to your LinkedIn profile
2. Click **More → Save to PDF**
3. Upload the PDF in the sidebar

### Option C: Demo Profile
Click **Load Demo Profile** to explore with a sample profile — no API key needed.

---

## 💬 Example Prompts

- `"Analyze my profile and give me a score"`
- `"Rewrite my headline for machine learning roles"`
- `"I want to apply for a Data Scientist role at Google — how do I fit?"`
- `"What skills am I missing for an ML engineer position?"`
- `"Give me a 6-month career roadmap"`

---

## 🔑 Tech Stack

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| LLM | Llama 3.3 70B via Groq |
| Agent Framework | LangGraph |
| LinkedIn Scraping | Apify (`anchor/linkedin-profile-enrichment`) |
| PDF Parsing | pdfplumber |
| Language | Python 3.10+ |

---

## 📄 License

MIT License — free to use and modify.
