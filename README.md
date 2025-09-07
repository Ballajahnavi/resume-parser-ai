#  Resume Parser AI + Dashboard

This project is part of the Habytat Internship technical evaluation.  
It provides an AI-powered tool to parse resumes (PDF/TXT) and display structured candidate information.

##  Features
- Upload PDF/TXT resumes (single or batch).
- Extract personal info, education, experience, skills, and certifications.
- REST API (FastAPI) for programmatic access and filtering.
- Interactive dashboard (Streamlit) with filtering by skill or degree.
- Privacy disclaimer and exception handling included.

##  Project Structure
- `app.py` → Streamlit frontend dashboard.
- `resume_parser.py` → Core resume parsing logic (spaCy + regex).
- `api.py` → FastAPI backend (resume upload + query endpoints).
- `requirements.txt` → Python dependencies.
- `README.md` → Project documentation.

##  Setup Instructions
1. Clone this repo or unzip the provided package.
2. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the dashboard:
   ```bash
   streamlit run app.py
   ```
4. Run the API server:
   ```bash
   uvicorn api:app --reload
   ```

##  Screenshots
Screenshots of the Streamlit dashboard and parsing results are included in the Word/PDF report.

## 📌 Notes
- This project is for demo/evaluation purposes only.
- Uploaded resumes are **not stored or shared externally**.
