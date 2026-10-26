"""End-to-end pipeline: resume -> candidate profile -> ranked jobs + skill gaps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .gap import GapResult, SkillGapAnalyzer, recommend_skills
from .matcher import DEFAULT_MODEL, SemanticMatcher, TfidfMatcher, calibrate_semantic
from .parser import ResumeProfile, parse_resume, required_experience_years, split_job_requirements
from .skills import SkillExtractor, get_skill_extractor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_JOBS = DATA_DIR / "jobs.json"

_COLUMN_ALIASES = {
    "title": ["title", "job_title", "job title", "position", "jobtitle", "role"],
    "description": ["description", "job_description", "job description", "jobdescription", "requirements"],
    "company": ["company", "company_name", "company name", "employer"],
    "category": ["category", "job_category", "industry"],
    "location": ["location", "job_location", "city"],
}


def load_jobs(path: str | Path = DEFAULT_JOBS, limit: int | None = None) -> pd.DataFrame:
    """Load jobs from JSON/CSV. Column names are normalised so common public
    datasets (e.g. Kaggle job postings) work without editing."""
    path = Path(path)
    df = pd.read_json(path) if path.suffix == ".json" else pd.read_csv(path)
    return normalize_jobs(df, limit)


def normalize_jobs(df: pd.DataFrame, limit: int | None = None) -> pd.DataFrame:
    lower = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for target, options in _COLUMN_ALIASES.items():
        for opt in options:
            if opt in lower:
                rename[lower[opt]] = target
                break
    df = df.rename(columns=rename)
    if "title" not in df or "description" not in df:
        raise ValueError("Jobs file needs 'title' and 'description' columns.")
    df = df.dropna(subset=["description"]).reset_index(drop=True)
    if limit:
        df = df.head(limit)
    for col in ("company", "category", "location"):
        if col not in df:
            df[col] = ""
    if "job_id" not in df:
        df["job_id"] = [f"J{i + 1:04d}" for i in range(len(df))]
    df[["company", "category", "location"]] = df[["company", "category", "location"]].fillna("")
    return df


@dataclass
class MatchResult:
    profile: ResumeProfile
    ranking: pd.DataFrame           # one row per job, sorted by the chosen method
    gaps: dict[str, GapResult]      # job_id -> gap
    recommendations: pd.DataFrame   # skills to learn, aggregated over the top-K jobs


class MatchingPipeline:
    def __init__(self, jobs: pd.DataFrame, model_name: str = DEFAULT_MODEL,
                 extractor: SkillExtractor | None = None, semantic: SemanticMatcher | None = None):
        self.jobs = jobs.reset_index(drop=True).copy()
        self.extractor = extractor or get_skill_extractor()

        # Structured job profiles: required vs preferred skills, min. experience.
        req_skills, pref_skills, years = [], [], []
        for desc in self.jobs["description"]:
            req_text, pref_text = split_job_requirements(desc)
            req = self.extractor.extract(req_text)
            pref = [s for s in self.extractor.extract(pref_text) if s not in req]
            req_skills.append(req)
            pref_skills.append(pref)
            years.append(required_experience_years(req_text))
        self.jobs["required_skills"] = req_skills
        self.jobs["preferred_skills"] = pref_skills
        self.jobs["min_years"] = years

        self.job_texts = (self.jobs["title"] + ". " + self.jobs["description"]).tolist()
        self.tfidf = TfidfMatcher().fit(self.job_texts)
        self.semantic = semantic or SemanticMatcher(model_name)
        self.semantic.fit(self.job_texts)
        self.gap_analyzer = SkillGapAnalyzer(self.semantic)

    def profile(self, resume_text: str) -> ResumeProfile:
        profile = parse_resume(resume_text)
        profile.skills = self.extractor.extract(profile.raw_text)
        profile.skills_by_category = self.extractor.group_by_category(profile.skills)
        return profile

    def match(self, resume_text: str, method: str = "hybrid", top_k: int = 10,
              w_semantic: float = 0.5, w_skills: float = 0.4, w_experience: float = 0.1) -> MatchResult:
        """method: 'tfidf' (baseline), 'sbert' (semantic only) or 'hybrid'
        (calibrated SBERT + skill coverage + experience fit)."""
        profile = self.profile(resume_text)
        tfidf_scores = self.tfidf.score(profile.raw_text)
        sbert_scores = self.semantic.score(profile.raw_text)
        sem_norm = calibrate_semantic(sbert_scores)

        gaps, skill_scores, exp_scores = {}, [], []
        for _, job in self.jobs.iterrows():
            gap = self.gap_analyzer.analyze(profile.skills, job["required_skills"], job["preferred_skills"])
            gaps[job["job_id"]] = gap
            skill_scores.append(gap.skill_score)
            need = job["min_years"]
            exp_scores.append(1.0 if need == 0 else min(1.0, profile.experience_years / need))

        hybrid = []
        for s, k, e in zip(sem_norm, skill_scores, exp_scores):
            parts = [(w_semantic, s), (w_experience, e)]
            if k is not None:  # jobs with no recognised skills are scored without the skill term
                parts.append((w_skills, k))
            total_w = sum(w for w, _ in parts) or 1.0
            hybrid.append(sum(w * v for w, v in parts) / total_w)

        ranking = self.jobs[["job_id", "title", "company", "category", "location",
                             "required_skills", "preferred_skills", "min_years"]].copy()
        ranking["tfidf_score"] = tfidf_scores
        ranking["sbert_score"] = sbert_scores
        ranking["skill_score"] = [np.nan if k is None else k for k in skill_scores]
        ranking["experience_score"] = exp_scores
        ranking["hybrid_score"] = hybrid
        ranking["match_score"] = {"tfidf": tfidf_scores, "sbert": sbert_scores,
                                  "hybrid": np.array(hybrid)}[method]
        for col in ("tfidf_score", "sbert_score", "hybrid_score"):
            ranking[col.replace("_score", "_rank")] = ranking[col].rank(ascending=False, method="first").astype(int)
        ranking = ranking.sort_values("match_score", ascending=False).reset_index(drop=True)

        top = ranking.head(top_k)
        recs = recommend_skills([gaps[j] for j in top["job_id"]], top["title"].tolist(),
                                self.extractor.category_of)
        return MatchResult(profile, ranking, gaps, recs)

    def explain(self, resume_text: str, job_id: str, top_n: int = 3) -> list[dict]:
        idx = int(self.jobs.index[self.jobs["job_id"] == job_id][0])
        return self.semantic.explain(resume_text, self.jobs.at[idx, "description"], top_n)

    def keyword_overlap(self, resume_text: str, job_id: str, n: int = 10) -> list[str]:
        idx = int(self.jobs.index[self.jobs["job_id"] == job_id][0])
        return self.tfidf.top_terms(resume_text, idx, n)
