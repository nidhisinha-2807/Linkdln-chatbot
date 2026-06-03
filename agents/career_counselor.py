"""Career Counseling Agent — powered by Llama 3.3 70B via Groq (free)."""

import os
from groq import Groq
from prompts.prompt_templates import CAREER_COUNSELOR_PROMPT
from tools.linkedin_scraper import format_profile_for_prompt

MODEL = "llama-3.3-70b-versatile"


class CareerCounselorAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def counsel(self, profile_data: dict, target_role: str,
                user_message: str, memory_context: dict = None) -> str:
        profile_text = (
            format_profile_for_prompt(profile_data)
            if profile_data else "No profile provided."
        )
        current_situation = self._extract_situation(profile_data)

        career_goals = ""
        if memory_context:
            career_goals = memory_context.get("career_goals", "")
        if not career_goals:
            career_goals = target_role or "grow in current field"

        prompt = CAREER_COUNSELOR_PROMPT.format(
            profile_data=profile_text,
            target_role=target_role or career_goals,
            current_situation=current_situation,
            career_goals=career_goals,
        )
        prompt += f"\n\nUser's specific question: {user_message}"

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _extract_situation(self, profile_data: dict) -> str:
        if not profile_data:
            return "Profile not yet provided."
        lines = []
        if profile_data.get("experience"):
            latest = profile_data["experience"][0]
            lines.append(
                f"Current role: {latest.get('title')} at {latest.get('company')}"
            )
        lines.append(
            f"Number of positions: {len(profile_data.get('experience', []))}"
        )
        if profile_data.get("education"):
            edu = profile_data["education"][0]
            lines.append(
                f"Education: {edu.get('degree')} from {edu.get('school')}"
            )
        lines.append(f"Skills count: {len(profile_data.get('skills', []))}")
        return "\n".join(lines)