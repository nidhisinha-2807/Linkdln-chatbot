# 💼 LinkedIn Profile Optimizer — 100% Free

AI-powered LinkedIn coach using Google Gemini 1.5 Flash (free tier), LangGraph, and Streamlit.

## Free APIs Used

| Service | Free Tier | Purpose |
|---|---|---|
| Google Gemini 1.5 Flash | 15 RPM, 1M tokens/day | All AI responses |
| Proxycurl | 10 free credits | LinkedIn URL scraping |
| Streamlit Community Cloud | Free hosting | Deployment |

## Setup (5 minutes)

### 1. Get Free Gemini API Key
Go to https://aistudio.google.com/app/apikey → Sign in → Create API Key

### 2. Install
```bash
git clone https://github.com/yourusername/linkedin-optimizer
cd linkedin-optimizer

```

### 3. Configure
```bash
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

### 4. Run
```bash
streamlit run app.py
```

## Loading Your Profile (3 Free Methods)

**Method 1 — Paste (always free):**
Open LinkedIn → Ctrl+A → Ctrl+C → Paste in the sidebar

**Method 2 — URL via Proxycurl (10 free credits):**
Sign up at nubela.co/proxycurl → Add key to .env → Enter LinkedIn URL

**Method 3 — Demo Mode:**
Click "Demo Mode" to explore with a sample profile

## Deploy Free on Streamlit Cloud

1. Push code to GitHub
2. Go to share.streamlit.io
3. Connect repo, set GEMINI_API_KEY in Secrets
4. Deploy!