# resume_parser.py
import re
import spacy
from typing import List, Dict, Any

# Load spaCy NER once (disable heavy pipes for speed)
nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger"])

EMAIL_RE = re.compile(r'[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}')

# small canonical skills list to boost recall (extend as needed)
SKILL_KEYWORDS = [
    "python","java","c++","c","sql","pandas","numpy","tensorflow","pytorch",
    "react","angular","node","html","css","javascript","docker","kubernetes",
    "ml","machine learning","deep learning","nlp","pandas","matplotlib","seaborn",
    "git","aws","gcp","azure","sql"
]

def _first_person_name(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    # heuristic: top line short and capitalized -> name
    first = lines[0]
    if len(first.split()) <= 4 and first[0].isupper():
        return first
    # else fallback to spaCy PERSON
    doc = nlp(" ".join(lines[:6]))
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None

def extract_personal_info(text: str) -> Dict[str, Any]:
    try:
        name = _first_person_name(text)
        email_m = EMAIL_RE.search(text)
        phone_m = PHONE_RE.search(text)
        return {
            "name": name,
            "email": email_m.group(0) if email_m else None,
            "phone": phone_m.group(0) if phone_m else None
        }
    except Exception:
        return {"name": None, "email": None, "phone": None}

def _normalize_date_tokens(tokens: List[str]) -> List[str]:
    # reduce dates to common forms for display (keep original when possible)
    return tokens

def extract_education(text: str) -> List[Dict[str, Any]]:
    """
    More tolerant education extraction:
    - Detect various section headers (Education, Academics, Educational, Qualification)
    - If not present, scan whole text for degree keywords.
    - Split degree line by common separators ( -, |, – ) to separate degree/field/extra (CGPA).
    - Lookahead few lines for institute and dates.
    - Try to extract CGPA/GPA into a dedicated field `cgpa`.
    """
    education = []
    try:
        pattern = re.compile(
            r"(Education|Academics|Qualification|Educational|Academic Background|Education History).*?"
            r"(?=(?:\n(?:Experience|Projects|Skills|Certifications|Achievements|Work Experience|$)))",
            re.S | re.I
        )
        match = pattern.search(text)
        block = match.group(0) if match else text

        lines = [l.strip() for l in block.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if re.search(r"(Bachelor|Master|B\.Tech|M\.Tech|MBA|Ph\.D|BSc|MSc|Diploma|BE|B\.E\.)", line, re.I):
                edu = {}
                # split by common separators (dash, pipe, long dash) or multiple spaces
                parts = re.split(r"\s*[-–—|]\s*|\s{2,}", line)
                if parts:
                    edu["degree"] = parts[0].strip()
                if len(parts) > 1:
                    edu["field"] = parts[1].strip()
                if len(parts) > 2:
                    edu["extra"] = parts[2].strip()  # e.g., CGPA or honors

                # --- Attempt to extract CGPA/GPA into a dedicated field ---
                cgpa_match = None
                # 1) same line / parts with explicit CGPA/GPA
                cgpa_match = re.search(
                    r"\b(?:CGPA|GPA)\b[:\s-]*([0-9](?:\.\d+)?(?:/[0-9]+)?)",
                    line, re.I
                )
                if not cgpa_match:
                    for p in parts:
                        m = re.search(r"\b(?:CGPA|GPA)\b[:\s-]*([0-9](?:\.\d+)?(?:/[0-9]+)?)", p, re.I)
                        if m:
                            cgpa_match = m
                            break
                # 2) lookahead lines
                if not cgpa_match:
                    for j in range(i+1, min(i+4, len(lines))):
                        m = re.search(r"\b(?:CGPA|GPA)\b[:\s-]*([0-9](?:\.\d+)?(?:/[0-9]+)?)", lines[j], re.I)
                        if m:
                            cgpa_match = m
                            break
                # 3) fallback: patterns like '8.5/10'
                if not cgpa_match:
                    m2 = re.search(r"\b\d\.\d{1,2}\/\d{1,3}\b", line)
                    if m2:
                        edu["cgpa"] = m2.group(0)
                    else:
                        m3 = re.search(r"\b(?:CGPA|GPA)\b.*?(\d\.\d{1,2})", line, re.I)
                        if m3:
                            edu["cgpa"] = m3.group(1)
                else:
                    edu["cgpa"] = cgpa_match.group(1)
                    # remove cgpa text from extra if present
                    if "extra" in edu and isinstance(edu["extra"], str):
                        edu["extra"] = re.sub(
                            r"\b(?:CGPA|GPA)\b[:\s-]*[0-9](?:\.\d+)?(?:/[0-9]+)?",
                            "",
                            edu["extra"],
                            flags=re.I
                        ).strip()

                # dates on same line (MM/YYYY, YYYY, MMM YYYY)
                dates = re.findall(
                    r"(\d{2}/\d{4}|\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                    line, re.I
                )
                if dates:
                    if len(dates) >= 1:
                        edu["start_date"] = dates[0]
                    if len(dates) >= 2:
                        edu["end_date"] = dates[1]

                # lookahead up to 3 lines for institute, more dates, or cgpa
                for j in range(i+1, min(i+4, len(lines))):
                    nxt = lines[j]
                    if re.search(r"(University|College|Institute|School|Institute of Technology|IIT|NIT)", nxt, re.I) and "institution" not in edu:
                        edu["institution"] = nxt
                    more_dates = re.findall(
                        r"(\d{2}/\d{4}|\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                        nxt, re.I
                    )
                    if more_dates and "start_date" not in edu:
                        edu["start_date"] = more_dates[0]
                    if len(more_dates) > 1 and "end_date" not in edu:
                        edu["end_date"] = more_dates[1]
                    if "cgpa" not in edu:
                        m = re.search(r"\b(?:CGPA|GPA)\b[:\s-]*([0-9](?:\.\d+)?(?:/[0-9]+)?)", nxt, re.I)
                        if m:
                            edu["cgpa"] = m.group(1)

                # if the extracted fields are sparse, still include degree if present
                if edu.get("degree") or edu.get("institution"):
                    education.append(edu)

        # If none found by header scanning and education still empty, try a whole-text fallback:
        if not education:
            lines_all = [l.strip() for l in text.splitlines() if l.strip()]
            for i, line in enumerate(lines_all):
                if re.search(r"(Bachelor|Master|B\.Tech|M\.Tech|MBA|Ph\.D|BSc|MSc|Diploma|BE|B\.E\.)", line, re.I):
                    edu = {"degree": line}
                    # try lookahead same as above
                    for j in range(i+1, min(i+4, len(lines_all))):
                        nxt = lines_all[j]
                        if re.search(r"(University|College|Institute|School|Institute of Technology|IIT|NIT)", nxt, re.I):
                            edu["institution"] = nxt
                        dates = re.findall(
                            r"(\d{2}/\d{4}|\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                            nxt, re.I
                        )
                        if dates and "start_date" not in edu:
                            edu["start_date"] = dates[0]
                        if len(dates) > 1 and "end_date" not in edu:
                            edu["end_date"] = dates[1]
                        # cgpa fallback
                        m = re.search(r"\b(?:CGPA|GPA)\b[:\s-]*([0-9](?:\.\d+)?(?:/[0-9]+)?)", nxt, re.I)
                        if m:
                            edu["cgpa"] = m.group(1)
                    education.append(edu)
    except Exception:
        # fail gracefully
        return education

    return education


def extract_experience(text: str) -> List[Dict[str, Any]]:
    """
    Extract experience blocks:
    - Find Experience/Work Experience section if present, else whole text fallback.
    - Split by blank lines into chunks, try to parse role, company, dates and responsibilities.
    - Responsibilities are taken preferentially from bullet lines; fallback to short lines (not long paragraphs).
    """
    experiences = []
    try:
        pattern = re.compile(r"(Experience|Work Experience|Employment|Professional Experience).*?(?=(?:\n(?:Projects|Education|Skills|Certifications|$)))", re.S | re.I)
        match = pattern.search(text)
        block = match.group(0) if match else text

        chunks = re.split(r"\n\s*\n", block)
        for chunk in chunks:
            lines = [l.strip("•- *\t") for l in chunk.splitlines() if l.strip()]
            if not lines:
                continue
            role = lines[0]
            company = None
            # common patterns: "Role at Company", "Role - Company", or next line company with org name
            m_at = re.search(r"(?:at|@)\s+([A-Z][A-Za-z&\.\s-]{2,})", chunk)
            if m_at:
                company = m_at.group(1).strip()
            else:
                # try split by dash or pipe
                if "-" in role or "|" in role:
                    parts = re.split(r"\s*[-|]\s*", role)
                    if len(parts) > 1:
                        company = parts[1].strip()
                        role = parts[0].strip()

            # look for company in next line if it's capitalized and short
            if not company and len(lines) > 1 and re.search(r"[A-Z][a-zA-Z&\.\s]{2,}", lines[1]):
                candidate = lines[1]
                if len(candidate.split()) < 6 and re.search(r"[A-Za-z]", candidate):
                    company = candidate

            # dates: MM/YYYY, YYYY, MMM YYYY
            dates = re.findall(r"(\d{2}/\d{4}|\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", chunk, re.I)
            start, end = (dates[0] if dates else None), (dates[1] if len(dates) > 1 else None)

            # location heuristics
            loc_m = re.search(r"(Hyderabad|Bengaluru|Bangalore|Mumbai|Delhi|Chennai|Pune|Remote|India|United States|USA)", chunk, re.I)
            location = loc_m.group(0) if loc_m else None

            # Responsibilities extraction: prefer explicit bullets; fallback to short lines or first few sentences
            resp_items = re.findall(r"(?:•|-|\*|\d+\.)\s*([^\n]+)", chunk)
            responsibilities = []
            if resp_items:
                responsibilities = [r.strip() for r in resp_items if r.strip()]
            else:
                # fallback: take up to first 5 short lines after the role (avoid huge paragraphs)
                for ln in lines[1:6]:
                    if ln and len(ln) < 200:
                        responsibilities.append(ln)
                # final fallback: split long paragraph into sentences and take first 3
                if not responsibilities and len(lines) > 1:
                    para = " ".join(lines[1:])
                    sents = re.split(r'(?<=[\.\?\!])\s+', para)
                    responsibilities = [s.strip() for s in sents[:3] if s.strip()]

            experiences.append({
                "role": role,
                "company": company,
                "start_date": start,
                "end_date": end,
                "location": location,
                "responsibilities": responsibilities
            })
    except Exception:
        return experiences

    return experiences


def extract_skills(text: str) -> Dict[str, List[str]]:
    """
    Extract skills from a Skills section (if any) or fallback to keyword scanning.
    Returns a dict of categories -> list[str].
    """
    skills = {}
    try:
        pattern = re.compile(r"(Skills|Technical Skills|Core Skills|Areas of Expertise|Skillset).*?(?=(?:\n(?:Certifications|Projects|Experience|Education|$)))", re.S | re.I)
        match = pattern.search(text)
        block = match.group(0) if match else text

        # 1) category: values lines (Programming: Python, Java)
        for line in block.splitlines():
            if ":" in line and len(line) < 250:
                cat, vals = line.split(":", 1)
                if re.search(r"[A-Za-z]", cat):
                    items = [s.strip() for s in re.split(r"[,;/•\-|]", vals) if s.strip()]
                    if items:
                        skills[cat.strip()] = sorted(list(dict.fromkeys([i.title() for i in items])))

        # 2) bullet lists under skills heading
        if not skills and match:
            # try bullets (• -) or comma-separated
            items = re.findall(r"•\s*([^•\n]+)|-\s*([^-\\n]+)|(?:\n)([A-Za-z0-9+\#\.\s\-\_]{2,})", block)
            found = []
            for tup in items:
                for val in tup:
                    if val and len(val.strip()) > 1:
                        for part in re.split(r"[,;/•\-|]", val):
                            p = part.strip()
                            if p:
                                found.append(p)
            if found:
                skills["General"] = sorted(list(dict.fromkeys([s.title() for s in found if len(s) < 40])))

        # 3) fallback: keyword scan across whole text
        if not skills:
            found = set()
            text_low = text.lower()
            for kw in SKILL_KEYWORDS:
                if re.search(r"\b" + re.escape(kw) + r"\b", text_low, re.I):
                    found.add(kw.title())
            if found:
                skills["General"] = sorted(found)

    except Exception:
        return skills

    return skills



def extract_projects(text: str) -> List[Dict[str, Any]]:
    projects = []
    try:
        pattern = re.compile(r"(Projects|Selected Projects|Academic Projects).*?(?=(?:\n(?:Skills|Certifications|Experience|Education|$)))", re.S | re.I)
        match = pattern.search(text)
        block = match.group(0) if match else text
        chunks = re.split(r"\n\s*\n", block)
        for chunk in chunks:
            lines = [l.strip("∗-• ") for l in chunk.splitlines() if l.strip()]
            if not lines:
                continue
            title = lines[0]
            tech = re.findall(r"(Python|Java|C\+\+|SQL|PyTorch|TensorFlow|React|Angular|HTML|CSS|JavaScript|Pandas|NumPy)", chunk, re.I)
            date_m = re.search(r"(\d{2}/\d{4}|\d{4})", chunk)
            projects.append({
                "title": title,
                "tech": list(dict.fromkeys([t.title() for t in tech])),
                "date": date_m.group(0) if date_m else None,
                "description": " ".join(lines[1:])
            })
    except Exception:
        return projects
    return projects

def extract_certifications(text: str) -> List[str]:
    certs = []
    try:
        pattern = re.compile(r"(Certifications|Certification).*?(?=(?:\n(?:Projects|Skills|Experience|Education|$)))", re.S | re.I)
        match = pattern.search(text)
        block = match.group(0) if match else ""
        for line in block.splitlines():
            line = line.strip("∗-• ")
            if line and not re.search(r"certification", line, re.I):
                certs.append(line)
    except Exception:
        return certs
    return certs

def parse_resume(text: str) -> Dict[str, Any]:
    """
    Top-level parser. Each extractor is tolerant and returns [] or {} on failure.
    """
    try:
        return {
            "personal_info": extract_personal_info(text),
            "education": extract_education(text),
            "experience": extract_experience(text),
            "projects": extract_projects(text),
            "skills": extract_skills(text),
            "certifications": extract_certifications(text)
        }
    except Exception:
        return {
            "personal_info": {},
            "education": [],
            "experience": [],
            "projects": [],
            "skills": {},
            "certifications": []
        }
