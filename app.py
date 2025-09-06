# app.py
import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import datetime
import json
from resume_parser import parse_resume


st.set_page_config(page_title="📄 AI Resume Parser", layout="wide")
st.title("📄 AI Resume Parser")
st.caption("Upload resume(s) (PDF/TXT) to parse. Demo only — data is not stored externally.")

# CSS
st.markdown("""
    <style>
        body { background-color: #f4f6f9; }
        .tag {
            background: #f1f3f5;
            color: #333;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            border: 1px solid #d1d5db;
            display:inline-block;
            margin: 0.25rem 0.25rem 0.25rem 0;
        }
        .skill-row { display:flex; flex-wrap:wrap; gap:0.4rem; margin-top:0.5rem; }
        .section-title { font-weight:600; font-size:1.1rem; margin-top:0.6rem; }
    </style>
""", unsafe_allow_html=True)

# upload
uploaded_files = st.file_uploader("📤 Upload Resume(s)", type=["pdf", "txt"], accept_multiple_files=True)

if "resumes" not in st.session_state:
    st.session_state["resumes"] = []

if uploaded_files:
    new_results = []
    for uploaded in uploaded_files:
        try:
            content = uploaded.read()
            if uploaded.type == "application/pdf" or uploaded.name.lower().endswith(".pdf"):
                pdf = fitz.open(stream=content, filetype="pdf")
                text = "".join(page.get_text() for page in pdf)
            else:
                try:
                    text = content.decode("utf-8", errors="ignore")
                except:
                    text = str(content)
            parsed = parse_resume(text)
            parsed["filename"] = uploaded.name
            st.session_state["resumes"].append(parsed)
            new_results.append(parsed)
        except Exception as exc:
            st.error(f"Failed to parse {uploaded.name}: {exc}")

    if new_results:
        st.success(f"Parsed {len(new_results)} file(s) successfully.")

resumes = st.session_state.get("resumes", [])

# Candidate List & Filters
if resumes:
    st.subheader("📊 Candidate List")
    # build lists for filters
    skills_list = sorted({s for r in resumes for vals in r.get("skills", {}).values() for s in vals}) if resumes else []
    degrees_list = sorted({e.get("degree", "") for r in resumes for e in r.get("education", []) if e.get("degree")})

    colf1, colf2, colf3 = st.columns([3,3,2])
    skill_filter = colf1.multiselect("Filter by Skill", skills_list)
    degree_filter = colf2.multiselect("Filter by Degree", degrees_list)

    filtered = resumes
    if skill_filter:
        filtered = [r for r in filtered if any(sf in sum(r.get("skills", {}).values(), []) for sf in skill_filter)]
    if degree_filter:
        filtered = [r for r in filtered if any(df in (e.get("degree","") or "") for e in r.get("education", []) for df in degree_filter)]

    # DataFrame for list
    df_list = pd.DataFrame([{
        "Name": r.get("personal_info", {}).get("name"),
        "Email": r.get("personal_info", {}).get("email"),
        "Phone": r.get("personal_info", {}).get("phone"),
        "Skills": ", ".join(sum(r.get("skills", {}).values(), [])),
        "Education": " | ".join([", ".join(filter(None, [e.get("degree",""), e.get("field",""), e.get("extra","")])) for e in r.get("education", [])])
    } for r in filtered])

    st.dataframe(df_list, use_container_width=True, height=300)

    # Download all parsed resumes
    cold1, cold2 = st.columns(2)
    if cold1.button("⬇️ Download All (JSON)"):
        st.download_button("Download JSON", data=json.dumps(resumes, indent=2), file_name="all_resumes.json")
    cold2.write("")

# Resume details (select one)
if resumes:
    st.markdown("---")
    st.markdown("### Select resume to view details")
    filenames = [r["filename"] for r in resumes]
    selected = st.selectbox("Resume", filenames, index=0)
    result = next((r for r in resumes if r["filename"] == selected), resumes[0])

    # Personal Info
    st.markdown("### 👤 Personal Information")
    pi = result.get("personal_info", {})
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Name:** {pi.get('name') or '—'}")
    c2.write(f"**Email:** {pi.get('email') or '—'}")
    c3.write(f"**Phone:** {pi.get('phone') or '—'}")

    st.markdown("---")

    # Education (plain formatted text like requested)
    st.markdown("### 🎓 Education")
    edu = result.get("education", [])
    if edu:
        for e in edu:
            degree = e.get("degree", "—")
            field = e.get("field") or e.get("extra")
            institute = e.get("institution") or e.get("institute")
            start = e.get("start_date")
            end = e.get("end_date")
            import re
            cgpa = None
            extra = e.get("extra")
            if isinstance(extra, str) and "cgpa" in extra.lower():
                match = re.search(r"cgpa[:\s]*([0-9.]+)", extra, re.IGNORECASE)
                if match:
                    cgpa = match.group(1)
            # Print exactly like screenshot - bold degree + subsequent lines plain
            md = f"**{degree}**  \n"
            if field:
                md += f"{field}  \n"
            if institute:
                md += f"{institute}  \n"
            if start:
                md += f"Start Date: **{start}**  \n"
            if end:
                md += f"End Date: **{end}**  \n"
            if cgpa:
                md += f"CGPA: **{cgpa}**  \n"
            st.markdown(md)
    else:
        st.write("⚠️ No education details detected")

    st.markdown("---")

    # Experience
    st.markdown("### 💼 Experience")
    exp = result.get("experience", [])
    if exp:
        for e in exp:
            start = e.get("start_date")
            end = e.get("end_date")
            try:
                start_date = datetime.datetime.strptime(start, "%m/%Y") if start and "/" in start else (datetime.datetime.strptime(start, "%Y") if start and len(start) == 4 else None)
            except:
                start_date = None
            try:
                end_date = datetime.datetime.strptime(end, "%m/%Y") if end and "/" in end else (datetime.datetime.strptime(end, "%Y") if end and len(end) == 4 else datetime.datetime.today())
            except:
                end_date = datetime.datetime.today()

            if start_date:
                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                years = months // 12
                duration = f"{years} years" if years > 0 else f"{months} months"
            else:
                duration = "—"

            st.markdown(f"**Professional Experience ({duration})**")
            st.write(f"**{e.get('role', '—')}**")
            if e.get("company"):
                st.write(f"Company: {e.get('company')}")
            if e.get("location"):
                st.write(f"Location: {e.get('location')}")
            if start:
                st.write(f"Start Date: {start}")
            if end:
                st.write(f"End Date: {end}")
            if e.get("responsibilities"):
                st.write("Responsibilities:")
                for rline in e["responsibilities"]:
                    st.markdown(f"- {rline}")
            st.markdown("")
    else:
        st.write("—")

    st.markdown("---")

    # Skills (pills)
    st.markdown("### 🛠 Skills")
    skills = result.get("skills", {})
    if skills:
        all_skills = sum(skills.values(), [])
        if all_skills:
            tags_html = "".join([f"<span class='tag'>{s}</span>" for s in all_skills])
            st.markdown(f"<div class='skill-row'>{tags_html}</div>", unsafe_allow_html=True)
        else:
            st.write("—")
    else:
        st.write("—")

    st.markdown("---")

    # Certifications
    st.markdown("### 📜 Certifications")
    certs = result.get("certifications", [])
    if certs:
        for c in certs:
            st.markdown(f"- {c}")
    else:
        st.write("—")

    st.markdown("---")
    # Export single resume
    cexp1, cexp2 = st.columns(2)
    cexp1.download_button("⬇️ Download JSON", data=json.dumps(result, indent=2), file_name=f"{selected}.json")
    cexp2.download_button("⬇️ Download CSV", data=pd.DataFrame([result]).to_csv(index=False), file_name=f"{selected}.csv")

st.markdown("---")
st.caption("⚠️ Privacy Disclaimer: Uploaded resumes are processed only for demo purposes. No data is stored or shared externally.")
