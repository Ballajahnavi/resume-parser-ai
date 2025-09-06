# api.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import fitz
import json
from resume_parser import parse_resume

app = FastAPI(title="Resume Parser API (Demo)")

# In-memory store (replace with DB in production)
RESUMES = []

@app.post("/upload_resume")
async def upload_resume(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            content = await file.read()
            if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(".txt")):
                # skip unknown types
                continue
            if file.filename.lower().endswith(".pdf"):
                try:
                    pdf = fitz.open(stream=content, filetype="pdf")
                    text = "".join(page.get_text() for page in pdf)
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to read PDF {file.filename}: {e}")
            else:
                try:
                    text = content.decode("utf-8", errors="ignore")
                except:
                    text = str(content)
            parsed = parse_resume(text)
            parsed["filename"] = file.filename
            RESUMES.append(parsed)
            results.append(parsed)
        except Exception as exc:
            # partial failure: report error for this file
            results.append({"filename": file.filename, "error": str(exc)})
    return JSONResponse(content={"message": "Upload complete", "resumes": results})

@app.get("/resumes")
async def get_resumes(skill: Optional[str] = None, degree: Optional[str] = None):
    results = RESUMES
    if skill:
        results = [r for r in results if skill.lower() in " ".join(sum(r.get("skills", {}).values(), [])).lower()]
    if degree:
        results = [r for r in results if any(degree.lower() in (e.get("degree","") or "").lower() for e in r.get("education", []))]
    return {"resumes": results}

@app.get("/resumes/export")
async def export_resumes():
    return JSONResponse(content={"resumes": RESUMES})

@app.get("/")
async def root():
    return {"message": "Resume Parser API running"}
