"""Profile Analysis Agent — powered by Llama 3.3 70B via Groq (free)."""

import os
from groq import Groq
from prompts.prompt_templates import PROFILE_ANALYZER_PROMPT
from tools.linkedin_scraper import format_profile_for_prompt

MODEL = "llama-3.3-70b-versatile"


class ProfileAnalyzerAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def analyze(self, profile_data: dict, memory_context: dict = None) -> str:
        profile_text = format_profile_for_prompt(profile_data)
        prompt = PROFILE_ANALYZER_PROMPT.format(profile_data=profile_text)

        if memory_context and memory_context.get("career_goals"):
            prompt += f"\n\nUser's stated career goals: {memory_context['career_goals']}"

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content