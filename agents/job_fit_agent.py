"""Job Fit Analysis Agent — powered by Llama 3.3 70B via Groq (free)."""

import os
from groq import Groq
from prompts.prompt_templates import JOB_FIT_ANALYZER_PROMPT, JOB_DESCRIPTION_GENERATOR_PROMPT
from tools.linkedin_scraper import format_profile_for_prompt

MODEL = "llama-3.3-70b-versatile"


class JobFitAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def _generate_jd(self, job_role: str, company: str = "") -> str:
        """Generate a realistic job description for the role."""
        context = f"for {company}" if company else ""
        prompt = JOB_DESCRIPTION_GENERATOR_PROMPT.format(
            job_role=f"{job_role} {context}".strip()
        )
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.5,
        )
        return response.choices[0].message.content

    def analyze(self, profile_data: dict, job_role: str,
                company: str = "", memory_context: dict = None) -> str:
        if not job_role:
            job_role = "Software Engineer"

        job_description = self._generate_jd(job_role, company)
        profile_text = format_profile_for_prompt(profile_data)

        prompt = JOB_FIT_ANALYZER_PROMPT.format(
            profile_data=profile_text,
            job_role=job_role,
            company=company or "General",
            job_description=job_description,
        )

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.7,
        )
        return response.choices[0].message.content