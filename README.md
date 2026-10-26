# LinkedIn Profile Optimizer

A Streamlit career coach that uses Groq's GPT-OSS 120B model and specialist agents to review a LinkedIn profile, tailor profile content, and give job search guidance. Profiles can be loaded from a LinkedIn URL, a saved LinkedIn PDF, or demo data.

## Features

- Load a profile from a LinkedIn URL, PDF, or sample profile.
- Get profile feedback, role fit analysis, career guidance, and rewritten profile sections through chat.
- **New: Match a pasted job description against your profile.** The app reports an overall match score, profile evidence that fits the role, gaps in the available evidence, supported and unverified ATS keywords, and recommended profile edits. This update adds a dedicated sidebar matcher; it does not need the job title to be separately extracted by chat routing.
- Retain conversation context and career goals in session memory.

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a `.env` file and set `GROQ_API_KEY`. Get a key from [Groq Console](https://console.groq.com/).
4. Optionally set `APIFY_API_TOKEN` to enable LinkedIn URL scraping. PDF and demo profile loading do not use Apify.
5. Start the app:

   ```powershell
   streamlit run app.py
   ```

## Use the job description matcher

1. Load your profile in the sidebar (PDF or demo profile works without Apify).
2. Paste the job's responsibilities and qualifications into **Match a Job Description** in the sidebar.
3. Choose **Compare with my profile**. The comparison appears in the chat and is included in the current session conversation.

The matcher compares the supplied text with the profile currently loaded in the app. It does not fetch job listings or verify claims with an employer. Treat suggested keywords as prompts to check for accuracy; the model is instructed not to invent qualifications or metrics.

## Configuration

See [.env.example](.env.example) for the environment variable template. The app uses Groq for AI responses and Apify only for URL-based profile scraping.
