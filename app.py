"""
LinkedIn Profile Optimizer — Streamlit App
Groq (GPT-OSS 120B) + LangGraph + Apify URL scraping + LinkedIn PDF
"""

import streamlit as st
import os
import time
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="LinkedIn Profile Optimizer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

from memory.memory_manager import MemoryManager
from agents.orchestrator import Orchestrator
from tools.linkedin_scraper import (
    scrape_linkedin_url,
    parse_pdf_profile,
    create_demo_profile,
    format_profile_for_prompt,
)
from utils.helpers import get_greeting_message, get_profile_loaded_message

# ─────────────────────────────────────────────────────────────
# Dark Theme CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global dark base ── */
    #MainMenu, footer, header {visibility: hidden;}
    
    .stApp {
        background: #0a0a0f;
        color: #e2e8f0;
    }

    section[data-testid="stSidebar"] {
        background: #0d0d18 !important;
        border-right: 1px solid #1e1e3a;
    }

    /* ── Sidebar header ── */
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0 4px 0;
        margin-bottom: 4px;
    }
    .sidebar-brand-title {
        font-size: 1.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .free-badge {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    /* ── Section headers in sidebar ── */
    .sidebar-section-title {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #4b5563;
        margin: 16px 0 8px 0;
    }

    /* ── Tip box ── */
    .tip-box {
        background: rgba(99, 102, 241, 0.08);
        border-left: 3px solid #6366f1;
        padding: 10px 12px;
        border-radius: 0 8px 8px 0;
        font-size: 0.8rem;
        color: #a5b4fc;
        margin-bottom: 10px;
        line-height: 1.5;
    }

    /* ── Profile card in sidebar ── */
    .profile-card {
        background: linear-gradient(135deg, #1a1035 0%, #0f172a 100%);
        border: 1px solid #312e6e;
        border-radius: 12px;
        padding: 14px 16px;
        margin: 8px 0;
        position: relative;
        overflow: hidden;
    }
    .profile-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4);
    }
    .profile-name {
        font-size: 1rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 4px;
    }
    .profile-headline {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-bottom: 6px;
        line-height: 1.4;
    }
    .profile-location {
        font-size: 0.75rem;
        color: #64748b;
    }
    .open-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #10b981;
        font-size: 0.7rem;
        padding: 1px 8px;
        border-radius: 20px;
        margin-top: 4px;
    }

    /* ── Metrics ── */
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid #1e1e3a;
        border-radius: 10px;
        padding: 10px 12px !important;
    }
    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 0.7rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #a5b4fc !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }

    /* ── Quick action buttons ── */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #1e1e3a;
        background: rgba(255,255,255,0.03);
        color: #cbd5e1;
        font-size: 0.82rem;
        padding: 8px 12px;
        transition: all 0.2s ease;
        text-align: left;
    }
    .stButton > button:hover {
        border-color: #6366f1;
        background: rgba(99, 102, 241, 0.1);
        color: #a5b4fc;
        transform: translateX(2px);
    }
    .stButton > button:active {
        transform: translateX(0px);
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03);
        border-radius: 8px;
        padding: 3px;
        gap: 2px;
        border: 1px solid #1e1e3a;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px;
        color: #64748b;
        font-size: 0.78rem;
        padding: 4px 10px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.2) !important;
        color: #a5b4fc !important;
    }

    /* ── Text inputs ── */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15) !important;
    }

    /* ── File uploader ── */
    .stFileUploader > div {
        background: rgba(255,255,255,0.03) !important;
        border: 1px dashed #1e1e3a !important;
        border-radius: 8px !important;
    }

    /* ── Chat area ── */
    .chat-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 20px 0 16px 0;
        border-bottom: 1px solid #1e1e3a;
        margin-bottom: 20px;
    }
    .chat-header-icon {
        width: 42px;
        height: 42px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
    }
    .chat-header-title {
        font-size: 1.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .chat-header-sub {
        font-size: 0.82rem;
        color: #4b5563;
        margin-top: 1px;
    }

    /* ── Chat messages ── */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
    }

    [data-testid="stChatMessageContent"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
        line-height: 1.7 !important;
    }

    [data-testid="stChatMessageContent"] p {
        color: #e2e8f0 !important;
    }

    [data-testid="stChatMessageContent"] strong {
        color: #a5b4fc !important;
    }

    [data-testid="stChatMessageContent"] ul, 
    [data-testid="stChatMessageContent"] ol {
        color: #cbd5e1 !important;
    }

    /* User message different style */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
        background: rgba(99, 102, 241, 0.1) !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }

    /* ── Chat input ── */
    [data-testid="stChatInput"] {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid #1e1e3a !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15) !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #e2e8f0 !important;
        background: transparent !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #4b5563 !important;
    }

    /* ── Suggestion chips ── */
    .suggestion-chip {
        display: inline-block;
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.25);
        color: #a5b4fc;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        cursor: pointer;
        margin: 4px;
        transition: all 0.2s;
    }

    /* ── Divider ── */
    hr {
        border-color: #1e1e3a !important;
        margin: 12px 0 !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #6366f1 !important;
    }

    /* ── Toast ── */
    .stToast {
        background: #1a1035 !important;
        border: 1px solid #312e6e !important;
        color: #e2e8f0 !important;
    }

    /* ── Caption text ── */
    .stCaption {
        color: #374151 !important;
        font-size: 0.75rem !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: #1e1e3a;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover { background: #312e6e; }

    /* ── Memory status box ── */
    .memory-box {
        background: rgba(255,255,255,0.02);
        border: 1px solid #1e1e3a;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.78rem;
        color: #4b5563;
        margin-bottom: 8px;
    }
    .memory-box span {
        color: #6366f1;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────
def init_session():
    if "memory" not in st.session_state:
        st.session_state.memory = MemoryManager()
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = Orchestrator(st.session_state.memory)
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": get_greeting_message()}]
    if "profile_loaded" not in st.session_state:
        st.session_state.profile_loaded = False
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"thread_{int(time.time())}"


# ─────────────────────────────────────────────────────────────
# Profile Loaders
# ─────────────────────────────────────────────────────────────
def _set_profile(profile):
    st.session_state.memory.set_profile(profile, url=profile.get("profile_url", ""))
    st.session_state.profile_loaded = True
    msg = get_profile_loaded_message(profile)
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.session_state.memory.add_assistant_message(msg)


def load_profile_from_url(url: str):
    if not os.getenv("APIFY_API_TOKEN"):
        st.error("❌ APIFY_API_TOKEN not set in your .env file.")
        return
    with st.spinner("🌐 Fetching LinkedIn profile via Apify..."):
        try:
            profile = scrape_linkedin_url(url)
            _set_profile(profile)
            st.toast("Profile loaded!")
            st.session_state["url_success"] = True
        except Exception as e:
            st.session_state["url_error"] = str(e)


def load_profile_from_pdf(uploaded_file) -> bool:
    with st.spinner("📄 Parsing your LinkedIn PDF..."):
        try:
            pdf_bytes = uploaded_file.read()
            profile = parse_pdf_profile(pdf_bytes)
            if not profile.get("full_name") and not profile.get("about") and not profile.get("experience"):
                st.error("❌ Could not extract profile data.")
                return False
            _set_profile(profile)
            st.toast("Profile loaded!")
            return True
        except ImportError:
            st.error("❌ pdfplumber not installed. Run: pip install pdfplumber")
            return False
        except Exception as e:
            st.error(f"❌ {str(e)}")
            return False


def load_demo_profile():
    profile = create_demo_profile()
    _set_profile(profile)
    st.toast("🎭 Demo profile loaded!")


# ─────────────────────────────────────────────────────────────
# Message Processing
# ─────────────────────────────────────────────────────────────
def process_message(user_input: str):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner(""):
        try:
            response = st.session_state.orchestrator.process_message(
                user_message=user_input,
                thread_id=st.session_state.thread_id,
            )
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"⚠️ Error: {str(e)}\n\nPlease try again."
            })


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:

        # Brand
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">💼 LinkedIn Optimizer</div>
        </div>
        <span class="free-badge">GROQ</span>
        """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Load profile section
        st.markdown('<div class="sidebar-section-title">Load Your Profile</div>', unsafe_allow_html=True)

        tab_url, tab_pdf, tab_demo = st.tabs(["🔗 URL", "📄 PDF", "🎭 Demo"])

        with tab_url:
            st.markdown("""
            <div class="tip-box">
                Uses Apify (~$0.01/scrape from your $5 free credits).<br>
                Gets <b>all skills, experience, certifications</b> directly.
            </div>
            """, unsafe_allow_html=True)
            url_in = st.text_input(
                "LinkedIn URL",
                placeholder="https://linkedin.com/in/yourname",
                label_visibility="collapsed",
                key="url_input_field"
            )
            if st.button("🚀 Fetch Profile", use_container_width=True, key="fetch_btn"):
                if url_in and "linkedin.com/in/" in url_in:
                    load_profile_from_url(url_in)
                    if st.session_state.get("url_success"):
                        st.session_state.pop("url_success")
                        st.rerun()
                else:
                    st.error("Enter a valid linkedin.com/in/... URL")

            if st.session_state.get("url_error"):
                st.error(f"❌ {st.session_state.pop('url_error')}")

        with tab_pdf:
            st.markdown("""
            <div class="tip-box">
                LinkedIn → Your Profile → More → Save to PDF
            </div>
            """, unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Upload PDF", type=["pdf"],
                label_visibility="collapsed",
                key="pdf_uploader"
            )
            if uploaded:
                if st.button("✅ Load PDF", use_container_width=True, key="load_pdf_btn"):
                    if load_profile_from_pdf(uploaded):
                        st.rerun()

        with tab_demo:
            st.caption("Explore with a sample profile — no API needed")
            if st.button("🎭 Load Demo Profile", use_container_width=True, key="demo_btn"):
                load_demo_profile()
                st.rerun()

        st.markdown('<div class="sidebar-section-title">Match a Job Description</div>', unsafe_allow_html=True)
        with st.form("job_description_matcher"):
            job_description = st.text_area(
                "Paste a job description",
                placeholder="Paste the responsibilities and qualifications here...",
                height=180,
                max_chars=12000,
                label_visibility="collapsed",
            )
            match_submitted = st.form_submit_button("🎯 Compare with my profile", use_container_width=True)
        if match_submitted:
            if not st.session_state.profile_loaded:
                st.warning("Load a LinkedIn profile first, then compare it with the job description.")
            elif len(job_description.strip()) < 50:
                st.warning("Paste a fuller job description (at least 50 characters) for a useful comparison.")
            else:
                st.session_state.messages.append({"role": "user", "content": "Compare my profile with this pasted job description."})
                st.session_state.memory.add_user_message("Compared profile with a pasted job description.")
                try:
                    with st.spinner("Comparing your profile with the job requirements..."):
                        result = st.session_state.orchestrator.job_fit_agent.analyze_description(
                            st.session_state.memory.session.profile_data,
                            job_description.strip(),
                        )
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    st.session_state.memory.add_assistant_message(result)
                    st.session_state.memory.session.add_analyzed_job("Pasted job description")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not analyze this job description: {e}")

        st.markdown("<hr>", unsafe_allow_html=True)

        # Profile card
        if st.session_state.profile_loaded:
            profile = st.session_state.memory.session.profile_data
            if profile:
                name = profile.get("full_name", "User")
                headline = profile.get("headline", "")
                headline_short = headline[:60] + "..." if len(headline) > 60 else headline
                location = profile.get("location", "")
                open_to_work = profile.get("open_to_work", False)

                open_badge = '<br><span class="open-badge">🟢 Open to Work</span>' if open_to_work else ""

                st.markdown(f"""
                <div class="profile-card">
                    <div class="profile-name">{name}</div>
                    <div class="profile-headline">{headline_short}</div>
                    <div class="profile-location">📍 {location}</div>
                    {open_badge}
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Experience", f"{len(profile.get('experience', []))}")
                with c2:
                    st.metric("Skills", f"{len(profile.get('skills', []))}")

            st.markdown("<hr>", unsafe_allow_html=True)

        # Quick actions
        st.markdown('<div class="sidebar-section-title">Quick Actions</div>', unsafe_allow_html=True)

        quick = [
            ("📊  Analyze Profile",   "Please do a full analysis of my LinkedIn profile"),
            ("✍️  Rewrite Headline",  "Help me rewrite my LinkedIn headline"),
            ("📝  Improve About",     "Help me rewrite my About/Summary section"),
            ("🎯  Job Fit Check",     "I want to check my fit for a specific job role"),
            ("🚀  Career Roadmap",    "Give me a career roadmap and skill gap analysis"),
            ("💡  Quick Wins",        "What are the quickest improvements I can make to my profile?"),
        ]
        for label, action in quick:
            if st.button(label, use_container_width=True, key=f"qa_{label}"):
                process_message(action)
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Memory status
        st.markdown('<div class="sidebar-section-title">Session Memory</div>', unsafe_allow_html=True)
        mem = st.session_state.memory
        msg_count = len(mem.session.messages)
        goals = mem.session.career_goals
        jobs_analyzed = len(mem.session.analyzed_jobs)

        st.markdown(f"""
        <div class="memory-box">
            💬 Messages: <span>{msg_count}</span> &nbsp;|&nbsp;
            💼 Jobs: <span>{jobs_analyzed}</span>
            {"<br>🎯 Goals: <span>" + ", ".join(goals[:2]) + "</span>" if goals else ""}
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True, key="save_btn"):
                mem.save_session_end()
                st.success("Saved!")
        with col2:
            if st.button("🗑️ Reset", use_container_width=True, key="reset_btn"):
                for key in ["memory", "orchestrator", "messages", "profile_loaded", "thread_id"]:
                    st.session_state.pop(key, None)
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.72rem; color:#374151; line-height:1.8;">
            ⚡ Powered by Groq · GPT-OSS 120B<br>
            🔑 <a href="https://console.groq.com" target="_blank" style="color:#6366f1;">Get free Groq key</a> &nbsp;·&nbsp;
            <a href="https://apify.com" target="_blank" style="color:#6366f1;">Apify</a>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Main Chat UI
# ─────────────────────────────────────────────────────────────
def render_chat():

    # Header
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-icon">💼</div>
        <div>
            <div class="chat-header-title">Career Coach</div>
            <div class="chat-header-sub">AI-powered LinkedIn optimizer · Powered by GPT-OSS 120B</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Messages
    for msg in st.session_state.messages:
        avatar = "👤" if msg["role"] == "user" else "💼"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Suggestion chips after profile load
    if st.session_state.profile_loaded and len(st.session_state.messages) <= 3:
        st.markdown("""
        <div style="margin: 12px 0 8px 0; font-size: 0.8rem; color: #4b5563;">
            💡 Try asking:
        </div>
        """, unsafe_allow_html=True)

        suggestions = [
            "What's my profile score?",
            "What jobs can I apply for?",
            "Rewrite my headline for ML roles",
            "What skills am I missing?",
        ]
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(s, key=f"sug_{i}", use_container_width=True):
                    process_message(s)
                    st.rerun()

    # Chat input
    if user_input := st.chat_input("Ask about your profile, career goals, or job fit..."):
        process_message(user_input)
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────
def main():
    init_session()

    if not os.getenv("GROQ_API_KEY"):
        st.markdown("""
        <div style="
            max-width: 480px; margin: 80px auto; padding: 32px;
            background: rgba(99,102,241,0.08);
            border: 1px solid rgba(99,102,241,0.3);
            border-radius: 16px; text-align: center;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">🔑</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #a5b4fc; margin-bottom: 8px;">
                GROQ_API_KEY not set
            </div>
            <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 16px;">
                Add your free Groq API key to the .env file to get started.
            </div>
            <a href="https://console.groq.com" target="_blank" style="
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                color: white; padding: 10px 24px;
                border-radius: 8px; text-decoration: none;
                font-size: 0.85rem; font-weight: 600;
            ">Get Free API Key →</a>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
