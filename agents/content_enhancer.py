"""Content Enhancement Agent — powered by Llama 3.3 70B via Groq (free)."""

import os
from groq import Groq
from prompts.prompt_templates import CONTENT_ENHANCER_PROMPT
from tools.linkedin_scraper import format_profile_for_prompt

MODEL = "llama-3.3-70b-versatile"


class ContentEnhancerAgent:
    SECTION_MAP = {
        "headline": "headline",
        "about": "about",
        "summary": "about",
        "experience": "experience",
        "skills": "skills",
    }

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def enhance(self, profile_data: dict, section: str, target_role: str,
                user_message: str, memory_context: dict = None) -> str:
        profile_text = format_profile_for_prompt(profile_data)

        section_lower = section.lower() if section else ""
        if not section_lower:
            for key in self.SECTION_MAP:
                if key in user_message.lower():
                    section_lower = key
                    break
            if not section_lower:
                section_lower = "about"

        original = self._get_section_content(profile_data, section_lower)

        if not target_role and memory_context:
            target_role = memory_context.get("career_goals", "current industry")

        prompt = CONTENT_ENHANCER_PROMPT.format(
            profile_data=profile_text,
            target_role=target_role or "current industry",
            section=section_lower.title(),
            original_content=original,
        )

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _get_section_content(self, profile_data: dict, section: str) -> str:
        field = self.SECTION_MAP.get(section, section)
        content = profile_data.get(field, "")

        if isinstance(content, list):
            if section == "experience" and content:
                exp = content[0]
                return (
                    f"Title: {exp.get('title', '')}\n"
                    f"Company: {exp.get('company', '')}\n"
                    f"Description: {exp.get('description', '[None]')}"
                )
            elif section == "skills":
                return ", ".join(
                    s.get("name", s) if isinstance(s, dict) else s
                    for s in content[:15]
                )

        return str(content) if content else "[No content yet — create from scratch]"