"""
LinkedIn profile data handler.
Methods:
  1. Apify anchor/linkedin-profile-enrichment (URL scraping, pay-per-use ~$0.01/profile)
  2. LinkedIn PDF export (free, offline)
  3. Demo profile (no API needed)
"""

import io
import re
import os

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Method 1: Apify anchor/linkedin-profile-enrichment
# ─────────────────────────────────────────────────────────────

def scrape_linkedin_url(profile_url: str) -> dict:
    if not APIFY_AVAILABLE:
        raise ValueError("apify-client not installed. Run: pip install apify-client")

    api_token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not set in .env file.")

    if not re.search(r"linkedin\.com/in/[\w\-]+", profile_url):
        raise ValueError("Invalid LinkedIn URL. Example: https://www.linkedin.com/in/your-name")

    if not profile_url.startswith("http"):
        profile_url = "https://" + profile_url

    client = ApifyClient(api_token)

    run = client.actor("anchor/linkedin-profile-enrichment").call(
        run_input={"startUrls": [{"url": profile_url}]},
    )

    dataset_id = run.default_dataset_id  # ← fix here
    items = list(client.dataset(dataset_id).iterate_items())

    # TEMPORARY DEBUG - remove after checking
    import json
    print(json.dumps(items[0] if items else {}, indent=2))

    if not items:
        raise ValueError("No data returned. The profile may be private.")

    raw = items[0]
    if "error" in raw and len(raw) == 1:
        raise ValueError(f"Apify actor error: {raw['error']}")

    return _normalize(raw, profile_url)


def _normalize(raw: dict, profile_url: str) -> dict:
    # ── Experiences ───────────────────────────────────────────
    experience = []
    for pos in (raw.get("experiences") or []):
        if not isinstance(pos, dict):
            continue
        start = str(pos.get("starts_at") or "")
        end = str(pos.get("ends_at") or "Present")
        if end == start and end != "Present":
            end = "Present"
        experience.append({
            "title":       (pos.get("title") or "").strip(),
            "company":     (pos.get("company") or "").strip(),
            "location":    (pos.get("location") or "").strip(),
            "start_date":  start,
            "end_date":    end,
            "duration":    f"{start} – {end}".strip(" –"),
            "description": (pos.get("description") or "").strip()[:600],
        })

    # ── Education ─────────────────────────────────────────────
    education = []
    seen = set()
    for edu in (raw.get("education") or []):
        if not isinstance(edu, dict):
            continue
        school = (edu.get("school") or "").strip()
        degree = (edu.get("degree_name") or "").strip()
        key = school.lower()[:30]
        if not school or key in seen:
            continue
        seen.add(key)
        # Extract field from degree_name e.g. "Bachelor of Technology - BTech, Computer Science"
        field = ""
        fm = re.search(r",\s*(.+)$", degree)
        if fm:
            field = fm.group(1).strip()
        education.append({
            "school":     school,
            "degree":     degree,
            "field":      field,
            "start_date": str(edu.get("starts_at") or ""),
            "end_date":   str(edu.get("ends_at") or ""),
            "description": "",
        })

    # ── Skills ────────────────────────────────────────────────
    raw_skills = raw.get("skills") or []
    skills = []
    for s in raw_skills:
        if isinstance(s, str) and s.strip():
            skills.append({"name": s.strip(), "endorsements": 0})
        elif isinstance(s, dict):
            name = (s.get("name") or "").strip()
            if name:
                skills.append({"name": name, "endorsements": int(s.get("endorsements") or 0)})

    # ── Certifications ────────────────────────────────────────
    certifications = []
    for c in (raw.get("certifications") or []):
        if isinstance(c, dict):
            name = (c.get("name") or "").strip()
            issuer = (c.get("issuer") or c.get("authority") or "").strip()
            if name:
                certifications.append({"name": name, "issuer": issuer})
        elif isinstance(c, str) and c.strip():
            certifications.append({"name": c.strip(), "issuer": ""})

    # ── Languages ─────────────────────────────────────────────
    languages = []
    for lang in (raw.get("languages") or []):
        if isinstance(lang, dict):
            languages.append((lang.get("name") or lang.get("language") or "").strip())
        elif isinstance(lang, str):
            languages.append(lang.strip())
    languages = [l for l in languages if l]

    # ── Location ──────────────────────────────────────────────
    city = raw.get("city") or ""
    country = raw.get("country") or ""
    location = ", ".join(filter(None, [city, country]))

    return {
        "full_name":              (raw.get("full_name") or "").strip(),
        "headline":               (raw.get("headline") or "").strip(),
        "location":               location,
        "connections":            str(raw.get("connections") or ""),
        "followers":              str(raw.get("follower_count") or ""),
        "about":                  (raw.get("summary") or "").strip()[:2600],
        "experience":             experience[:10],
        "education":              education[:5],
        "skills":                 skills[:50],
        "certifications":         certifications[:15],
        "languages":              languages[:10],
        "recommendations_count":  int(raw.get("recommendations_count") or 0),
        "profile_url":            profile_url,
        "has_photo":              bool(raw.get("profile_pic_url")),
        "has_banner":             bool(raw.get("background_cover_image_url")),
        "open_to_work":           bool(raw.get("open_to_work")),
    }


# ─────────────────────────────────────────────────────────────
# Method 2: Parse LinkedIn PDF export
# ─────────────────────────────────────────────────────────────

def parse_pdf_profile(pdf_bytes: bytes, profile_url: str = "") -> dict:
    if not PDF_AVAILABLE:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

    profile = {
        "full_name": "", "headline": "", "location": "",
        "connections": "", "followers": "", "about": "",
        "experience": [], "education": [], "skills": [],
        "certifications": [], "languages": [],
        "recommendations_count": 0, "profile_url": profile_url,
        "has_photo": False, "has_banner": False,
    }

    left_lines, right_lines = _extract_two_columns(pdf_bytes)

    profile["skills"]         = _parse_sidebar_skills(left_lines)
    profile["certifications"] = _parse_sidebar_certifications(left_lines)
    _parse_main_content(right_lines, profile)

    # Infer extra skills from experience/about text
    all_text = profile.get("about", "") + " " + " ".join(
        e.get("description", "") for e in profile["experience"]
    )
    extra = _infer_skills_from_text(all_text, existing=profile["skills"])
    profile["skills"].extend(extra)

    return profile


def _extract_two_columns(pdf_bytes: bytes):
    SPLIT_X = 200
    left_rows, right_rows = {}, {}
    offset = 0

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for w in (page.extract_words() or []):
                top = round((w["top"] + offset) / 4) * 4
                bucket = left_rows if w["x0"] < SPLIT_X else right_rows
                bucket.setdefault(top, []).append((w["x0"], w["text"]))
            offset += page.height

    def to_lines(rows):
        return [
            " ".join(t for _, t in sorted(rows[k]))
            for k in sorted(rows)
            if " ".join(t for _, t in sorted(rows[k])).strip()
        ]

    return to_lines(left_rows), to_lines(right_rows)


def _parse_sidebar_skills(lines: list) -> list:
    skills, in_skills = [], False
    stop = re.compile(r"^(certifications?|licenses?|languages?|contact|awards?|volunteer|honors|publications)$", re.I)
    for line in lines:
        if line.strip().lower() == "top skills":
            in_skills = True
            continue
        if in_skills:
            if stop.match(line.strip()):
                break
            clean = line.strip()
            if clean and len(clean) < 60:
                skills.append({"name": clean, "endorsements": 0})
            if len(skills) >= 10:
                break
    return skills


def _parse_sidebar_certifications(lines: list) -> list:
    certs, in_certs, buffer = [], False, []
    stop = re.compile(r"^(top skills|languages?|contact|awards?|volunteer|honors|publications)$", re.I)
    for line in lines:
        if line.strip().lower() in ("certifications", "licenses & certifications"):
            in_certs = True
            continue
        if in_certs:
            if stop.match(line.strip()):
                break
            if line.strip():
                buffer.append(line.strip())

    CERT_START = re.compile(r"^(aws|tata|accenture|google|microsoft|coursera|udemy|ibm|meta|linkedin|oracle|cisco)", re.I)
    current = []
    for line in buffer:
        if current and (CERT_START.match(line) or (re.match(r"^[A-Z]", line) and
                not current[-1].endswith((":", ",", "and", "of", "-", "Data", "Effective")))):
            certs.append({"name": " ".join(current), "issuer": ""})
            current = [line]
        else:
            current.append(line)
    if current:
        certs.append({"name": " ".join(current), "issuer": ""})
    return certs[:15]


def _parse_main_content(lines: list, profile: dict):
    # Name
    for line in lines[:5]:
        m = re.search(r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", line)
        if m:
            profile["full_name"] = m.group(1)
            break

    # Headline
    hl_re = re.compile(r"(engineer|scientist|developer|analyst|intern|graduate|manager|designer|fresher|student)", re.I)
    for line in lines[:8]:
        if "|" in line or hl_re.search(line):
            profile["headline"] = line.strip()
            break

    # Location
    loc_re = re.compile(r"(area|region|bangalore|mumbai|delhi|pune|hyderabad|chennai|nagpur|india|remote|greater|maharashtra)", re.I)
    for line in lines[:10]:
        if loc_re.search(line) and len(line) < 60 and "@" not in line:
            profile["location"] = line.strip()
            break

    SECTION_MAP = {
        "summary": "about", "experience": "experience",
        "education": "education", "languages": "languages",
    }
    current_section = None
    section_content = {}

    for line in lines:
        ll = line.lower().strip()
        if ll in SECTION_MAP:
            current_section = SECTION_MAP[ll]
            section_content.setdefault(current_section, [])
        elif current_section and not re.match(r"^page\s+\d+", line, re.I):
            section_content[current_section].append(line)

    if "about" in section_content:
        profile["about"] = " ".join(section_content["about"])[:2600]
    if "experience" in section_content:
        profile["experience"] = _parse_experience(section_content["experience"])
    if "education" in section_content:
        profile["education"] = _parse_education(section_content["education"])
    if "languages" in section_content:
        profile["languages"] = [l for l in section_content["languages"] if l and len(l) < 50][:10]


def _parse_experience(lines: list) -> list:
    entries, current, desc_lines = [], {}, []
    date_re = re.compile(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}",
        re.I
    )

    def is_date(line):
        return bool(date_re.search(line)) and len(line) < 90

    def save():
        if current:
            c = dict(current)
            c["description"] = " ".join(desc_lines).strip()
            entries.append(c)

    for line in lines:
        clean = line.lstrip("•").strip()
        if is_date(line):
            save()
            current = {"title": "", "company": "", "location": "",
                       "start_date": "", "end_date": "Present",
                       "description": "", "duration": line}
            desc_lines = []
        elif current and not current["title"] and len(clean) < 120:
            current["title"] = clean
        elif current and not current["company"] and len(clean) < 120:
            current["company"] = clean
        elif current:
            desc_lines.append(clean)
    save()
    return entries[:10]


def _parse_education(lines: list) -> list:
    entries, seen, i = [], set(), 0
    clean = [l for l in lines if not re.match(r"^page\s+\d+", l, re.I) and l.strip()]
    while i < len(clean):
        school = clean[i]
        degree_line = clean[i + 1] if i + 1 < len(clean) else ""
        key = school.lower()[:30]
        if key not in seen and len(school) > 3:
            seen.add(key)
            field = ""
            fm = re.search(r",\s*(.+?)(?:\s*·|\s*\(|$)", degree_line)
            if fm:
                field = fm.group(1).strip()
            start, end = "", ""
            dm = re.search(r"(\w+ \d{4}|\d{4})\s*[-–·]\s*(\w+ \d{4}|\d{4})", degree_line)
            if dm:
                start, end = dm.group(1), dm.group(2)
            entries.append({"school": school, "degree": degree_line,
                             "field": field, "start_date": start,
                             "end_date": end, "description": ""})
        i += 3
    return entries[:5]


def _infer_skills_from_text(text: str, existing: list) -> list:
    TECH = re.compile(
        r"\b(python|sql|mysql|php|html|css|javascript|react|django|fastapi|"
        r"flask|java\b|c\+\+|tableau|power bi|excel|git|docker|kubernetes|"
        r"aws|azure|gcp|tensorflow|pytorch|keras|scikit.learn|pandas|numpy|"
        r"matplotlib|seaborn|plotly|folium|geopandas|bert|nlp|llm|langchain|"
        r"k.means|clustering|pca|xgboost|random forest|facebook prophet|"
        r"prophet|haversine|logistic regression|machine learning|deep learning|"
        r"data science|geospatial|time series|forecasting|streamlit|"
        r"postgresql|mongodb|sentence.bert|sentence bert)\b",
        re.I
    )
    existing_names = {s["name"].lower() for s in existing}
    found = {}
    for m in TECH.finditer(text):
        name = m.group(0)
        if name.lower() not in existing_names and name.lower() not in found:
            found[name.lower()] = {"name": name, "endorsements": 0}
    return list(found.values())[:20]


# ─────────────────────────────────────────────────────────────
# Format profile for LLM prompts
# ─────────────────────────────────────────────────────────────

def format_profile_for_prompt(profile: dict) -> str:
    s = []
    s.append(f"**Name:** {profile.get('full_name', 'N/A')}")
    s.append(f"**Headline:** {profile.get('headline', 'N/A')}")
    s.append(f"**Location:** {profile.get('location', 'N/A')}")
    if profile.get("followers"):
        s.append(f"**Followers:** {profile['followers']}")
    if profile.get("open_to_work"):
        s.append("**Open to Work:** Yes")

    s.append(f"\n**About/Summary:**\n{profile['about'][:1500]}"
             if profile.get("about") else "\n**About/Summary:** [NOT PROVIDED]")

    if profile.get("experience"):
        s.append("\n**Experience:**")
        for exp in profile["experience"][:5]:
            s.append(f"- {exp.get('title','N/A')} at {exp.get('company','N/A')} ({exp.get('duration','')})")
            if exp.get("description"):
                s.append(f"  {exp['description'][:300]}")
    else:
        s.append("\n**Experience:** [NOT PROVIDED]")

    if profile.get("education"):
        s.append("\n**Education:**")
        for edu in profile["education"]:
            s.append(f"- {edu.get('degree','')} from {edu.get('school','N/A')} ({edu.get('start_date','')}–{edu.get('end_date','')})")

    if profile.get("skills"):
        names = [sk.get("name", sk) if isinstance(sk, dict) else sk for sk in profile["skills"][:25]]
        s.append(f"\n**Skills ({len(profile['skills'])} total):** {', '.join(names)}")
    else:
        s.append("\n**Skills:** [NOT PROVIDED]")

    if profile.get("certifications"):
        s.append("\n**Certifications:**")
        for c in profile["certifications"][:8]:
            name = c.get("name", c) if isinstance(c, dict) else c
            issuer = c.get("issuer", "") if isinstance(c, dict) else ""
            s.append(f"- {name}" + (f" ({issuer})" if issuer else ""))

    if profile.get("languages"):
        s.append(f"\n**Languages:** {', '.join(profile['languages'])}")

    return "\n".join(s)


# ─────────────────────────────────────────────────────────────
# Demo profile
# ─────────────────────────────────────────────────────────────

def create_demo_profile() -> dict:
    return {
        "full_name": "Priya Sharma",
        "headline": "Software Engineer | Python | Django | Looking for ML roles",
        "location": "Bangalore, India",
        "connections": "412", "followers": "530",
        "about": "Passionate software engineer with 3 years of experience building scalable web applications. Proficient in Python, Django, and REST APIs. Currently upskilling in Machine Learning.",
        "experience": [
            {"title": "Software Engineer", "company": "Infosys", "location": "Bangalore",
             "start_date": "2022", "end_date": "Present",
             "description": "Built REST APIs using Django and FastAPI serving 50k daily users. Optimized database queries reducing load time by 30%.",
             "duration": "2022 – Present"},
            {"title": "Junior Developer", "company": "Startupzone", "location": "Remote",
             "start_date": "2021", "end_date": "2021",
             "description": "Developed React frontend. Fixed bugs.", "duration": "2021"},
        ],
        "education": [{"school": "VIT University", "degree": "B.Tech", "field": "Computer Science",
                        "start_date": "2017", "end_date": "2021", "description": ""}],
        "skills": [{"name": n, "endorsements": 0} for n in
                   ["Python", "Django", "REST APIs", "SQL", "Git", "Machine Learning", "React", "Docker"]],
        "certifications": [{"name": "AWS Certified Developer", "issuer": "Amazon Web Services"}],
        "languages": ["English", "Hindi"],
        "recommendations_count": 1,
        "profile_url": "https://linkedin.com/in/demo",
        "has_photo": True, "has_banner": False,
    }