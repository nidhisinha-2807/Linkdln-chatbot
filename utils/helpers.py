"""Utility functions."""

import re
from urllib.parse import urlparse


def is_valid_linkedin_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        return "linkedin.com" in parsed.netloc and "/in/" in parsed.path
    except Exception:
        return False


def extract_linkedin_url_from_text(text: str) -> str:
    pattern = r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+'
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def get_greeting_message() -> str:
    return """**Hi, I'm your LinkedIn career advisor.**

Load your LinkedIn profile from the sidebar to get started.

I can help you with profile scoring, job fit analysis, rewriting your headline and about section, and building a career roadmap."""


def get_profile_loaded_message(profile: dict) -> str:
    name = profile.get("full_name", "there")
    headline = profile.get("headline", "your current role")
    skill_count = len(profile.get("skills", []))
    exp_count = len(profile.get("experience", []))
    about_status = "✓" if profile.get("about") else "✗ Missing"
    edu_status = "✓" if profile.get("education") else "✗ Missing"

    return f"""✅ Profile loaded!

Name: {name}
Role: {headline}

Quick stats:
- 💼 {exp_count} experience entries
- 🛠️ {skill_count} skills
- 📝 About: {about_status}
- 🎓 Education: {edu_status}

What do you want to do?
1. 📊 Full profile analysis + score
2. 🎯 Analyze fit for a specific job role
3. ✍️ Rewrite headline / about / experience
4. 🚀 Career advice and skill gap analysis

Type your choice or use the Quick Actions in the sidebar!"""