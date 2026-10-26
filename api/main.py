"""REST API for the Angular frontend.

Run:  uvicorn api.main:app --port 8000
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import json
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.matcher import AVAILABLE_MODELS, DEFAULT_MODEL, SemanticMatcher
from src.parser import extract_text
from src.pipeline import (DEFAULT_JOBS, DEFAULT_WEIGHTS, MatchingPipeline, job_row_to_dict, load_jobs,
                          normalize_jobs, result_to_dict)
from src.skills import get_skill_extractor

ROOT = Path(__file__).resolve().parent.parent
CUSTOM_JOBS = ROOT / "data" / "custom_jobs.json"
SAMPLES = ROOT / "data" / "sample_resumes"
RESULTS = ROOT / "results" / "eval_results.json"
FRONTEND_DIST = ROOT / "frontend" / "dist" / "frontend" / "browser"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
METHODS = {"hybrid": "Hybrid (SBERT + skills + experience + education)",
           "sbert": "SBERT semantic similarity", "tfidf": "TF-IDF baseline"}


class Engine:
    """Holds loaded models and one pipeline per model; rebuilt when jobs change."""

    def __init__(self):
        self.lock = threading.RLock()
        self.extractor = get_skill_extractor()
        self.semantic: dict[str, SemanticMatcher] = {}
        self.pipelines: dict[str, MatchingPipeline] = {}

    def model(self, name: str) -> SemanticMatcher:
        with self.lock:
            if name not in self.semantic:
                self.semantic[name] = SemanticMatcher(name)
            return self.semantic[name]

    def jobs(self) -> pd.DataFrame:
        builtin = load_jobs(DEFAULT_JOBS)
        builtin["source"] = "builtin"
        custom = read_custom_jobs()
        if custom:
            extra = normalize_jobs(pd.DataFrame(custom))
            extra["source"] = "custom"
            return pd.concat([builtin, extra], ignore_index=True)
        return builtin

    def pipeline(self, model: str = DEFAULT_MODEL) -> MatchingPipeline:
        with self.lock:
            if model not in self.pipelines:
                self.pipelines[model] = MatchingPipeline(self.jobs(), extractor=self.extractor,
                                                         semantic=self.model(model))
            return self.pipelines[model]

    def invalidate(self):
        with self.lock:
            self.pipelines.clear()


def read_custom_jobs() -> list[dict]:
    return json.loads(CUSTOM_JOBS.read_text(encoding="utf-8")) if CUSTOM_JOBS.exists() else []


def write_custom_jobs(jobs: list[dict]):
    CUSTOM_JOBS.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


engine = Engine()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load the default model in the background so the first request is fast.
    threading.Thread(target=engine.pipeline, daemon=True).start()
    yield


app = FastAPI(title="Resume–Job Matching & Skill Gap API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:4200"], allow_methods=["*"],
                   allow_headers=["*"])


def check_model(model: str) -> str:
    if model not in AVAILABLE_MODELS.values():
        raise HTTPException(400, f"Unknown model '{model}'")
    return model


# ----------------------------------------------------------------------------- meta

@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": list(engine.semantic), "ready": DEFAULT_MODEL in engine.pipelines}


@app.get("/api/config")
def config():
    return {
        "models": [{"id": v, "label": k} for k, v in AVAILABLE_MODELS.items()],
        "default_model": DEFAULT_MODEL,
        "methods": [{"id": k, "label": v} for k, v in METHODS.items()],
        "default_weights": DEFAULT_WEIGHTS,
        "samples": sorted(p.name for p in SAMPLES.glob("*.txt")),
    }


@app.get("/api/samples/{name}")
def sample(name: str):
    path = SAMPLES / name
    if not re.fullmatch(r"[\w\-]+\.txt", name) or not path.exists():
        raise HTTPException(404, "Sample not found")
    return {"name": name, "text": path.read_text(encoding="utf-8")}


@app.get("/api/skills")
def skills():
    ex = engine.extractor
    grouped: dict[str, list[str]] = {}
    for skill, cat in sorted(ex.category_of.items()):
        grouped.setdefault(cat, []).append(skill)
    return {"total": len(ex.category_of), "categories": grouped}


# ----------------------------------------------------------------------------- jobs

class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    company: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=80)
    description: str = Field(min_length=40, max_length=20000)


def _job_dict(pipe: MatchingPipeline, row: pd.Series) -> dict:
    return {"job_id": row["job_id"], "title": row["title"], "company": row["company"],
            "category": row["category"], "location": row["location"], "description": row["description"],
            "required_skills": list(row["required_skills"]), "preferred_skills": list(row["preferred_skills"]),
            "min_years": float(row["min_years"]), "required_degree": row["required_degree"],
            "source": row.get("source", "builtin")}


@app.get("/api/jobs")
def list_jobs(q: str = "", category: str = ""):
    pipe = engine.pipeline()
    df = pipe.jobs
    if category:
        df = df[df["category"] == category]
    if q:
        mask = (df["title"] + " " + df["company"] + " " + df["description"]).str.contains(q, case=False, regex=False)
        df = df[mask]
    return {"total": len(pipe.jobs), "categories": sorted(c for c in pipe.jobs["category"].unique() if c),
            "jobs": [_job_dict(pipe, row) for _, row in df.iterrows()]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    pipe = engine.pipeline()
    rows = pipe.jobs[pipe.jobs["job_id"] == job_id]
    if rows.empty:
        raise HTTPException(404, "Job not found")
    return _job_dict(pipe, rows.iloc[0])


@app.post("/api/jobs", status_code=201)
def add_job(job: JobIn):
    custom = read_custom_jobs()
    next_id = max([int(j["job_id"][1:]) for j in custom] + [0]) + 1
    record = {"job_id": f"C{next_id:03d}", **job.model_dump()}
    custom.append(record)
    write_custom_jobs(custom)
    engine.invalidate()
    return get_job(record["job_id"])


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    custom = read_custom_jobs()
    remaining = [j for j in custom if j["job_id"] != job_id]
    if len(remaining) == len(custom):
        raise HTTPException(400, "Only jobs you added can be deleted")
    write_custom_jobs(remaining)
    engine.invalidate()


# ----------------------------------------------------------------------------- analysis

async def _resume_text(file: UploadFile | None, text: str | None, sample_name: str | None) -> str:
    if file is not None and file.filename:
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File is larger than 5 MB")
        try:
            return extract_text(data, file.filename)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        except Exception as e:  # noqa: BLE001 - corrupt / encrypted files
            raise HTTPException(400, f"Could not read the file: {e}") from e
    if text and text.strip():
        return text
    if sample_name:
        return sample(sample_name)["text"]
    raise HTTPException(400, "Provide a resume file, text or sample name")


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), text: str | None = Form(None),
                  sample_name: str | None = Form(None), method: str = Form("hybrid"),
                  model: str = Form(DEFAULT_MODEL), top_k: int = Form(10),
                  w_semantic: float = Form(DEFAULT_WEIGHTS["semantic"]),
                  w_skills: float = Form(DEFAULT_WEIGHTS["skills"]),
                  w_experience: float = Form(DEFAULT_WEIGHTS["experience"]),
                  w_education: float = Form(DEFAULT_WEIGHTS["education"]),
                  infer_skills: bool = Form(False)):
    if method not in METHODS:
        raise HTTPException(400, f"Unknown method '{method}'")
    resume = await _resume_text(file, text, sample_name)
    if len(resume.split()) < 20:
        raise HTTPException(422, "Very little text could be read from this resume. "
                                 "If it is a scanned PDF, please upload a text-based PDF or DOCX.")
    pipe = engine.pipeline(check_model(model))
    result = pipe.match(resume, method=method, top_k=max(1, min(top_k, 50)), w_semantic=w_semantic,
                        w_skills=w_skills, w_experience=w_experience, w_education=w_education,
                        infer_skills=infer_skills)
    out = result_to_dict(result, top_k)
    out["settings"] = {"method": method, "model": model, "top_k": top_k, "infer_skills": infer_skills,
                       "weights": {"semantic": w_semantic, "skills": w_skills, "experience": w_experience,
                                   "education": w_education},
                       "source": file.filename if file is not None and file.filename else sample_name or "pasted text"}
    return out


@app.post("/api/extract-text")
async def extract(file: UploadFile = File(...)):
    text = await _resume_text(file, None, None)
    return {"filename": file.filename, "text": text, "words": len(text.split())}


class ExplainIn(BaseModel):
    resume_text: str
    job_id: str
    model: str = DEFAULT_MODEL


@app.post("/api/explain")
def explain(body: ExplainIn):
    pipe = engine.pipeline(check_model(body.model))
    if body.job_id not in set(pipe.jobs["job_id"]):
        raise HTTPException(404, "Job not found")
    return {"evidence": pipe.explain(body.resume_text, body.job_id, top_n=4),
            "keywords": pipe.keyword_overlap(body.resume_text, body.job_id, 12)}


class CustomMatchIn(BaseModel):
    resume_text: str = Field(min_length=50)
    title: str = ""
    description: str = Field(min_length=40)
    model: str = DEFAULT_MODEL
    infer_skills: bool = False


@app.post("/api/match-custom")
def match_custom(body: CustomMatchIn):
    pipe = engine.pipeline(check_model(body.model))
    result, job_id = pipe.match_custom_job(body.resume_text, body.title, body.description,
                                           infer_skills=body.infer_skills)
    row = result.ranking[result.ranking["job_id"] == job_id].iloc[0]
    match = job_row_to_dict(row, result.gaps[job_id], int(row["hybrid_rank"]))
    match["rank_among"] = len(result.ranking)  # its rank if it were added to the job collection
    evidence = pipe.semantic.explain(body.resume_text, body.description, top_n=4)
    return {"match": match, "evidence": evidence, "candidate_skills": result.profile.all_skills}


# ----------------------------------------------------------------------------- evaluation

@app.get("/api/evaluation")
def get_evaluation():
    if not RESULTS.exists():
        raise HTTPException(404, "No evaluation results yet")
    return json.loads(RESULTS.read_text(encoding="utf-8"))


class EvalIn(BaseModel):
    model: str = DEFAULT_MODEL


@app.post("/api/evaluation/run")
def run_evaluation(body: EvalIn):
    import evaluate as ev
    # The annotations reference the built-in jobs, so evaluate on those only.
    pipe = MatchingPipeline(load_jobs(DEFAULT_JOBS), extractor=engine.extractor,
                            semantic=engine.model(check_model(body.model)))
    results = ev.evaluate_annotated(pipe)
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8")
    (RESULTS.parent / "eval_results.md").write_text(ev.to_markdown(results), encoding="utf-8")
    return results


# ----------------------------------------------------------------------------- frontend (production build)

if FRONTEND_DIST.exists():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (FRONTEND_DIST / path).resolve()
        if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
