"""End-to-end pipeline: resume -> candidate profile -> ranked jobs + skill gaps."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .gap import GapResult, SkillGapAnalyzer, recommend_skills
from .matcher import DEFAULT_MODEL, SemanticMatcher, TfidfMatcher, calibrate_semantic
from .parser import (DEGREE_RANK, ResumeProfile, parse_resume, required_degree, required_experience_years,
                     split_job_requirements)
from .quality import assess_quality
from .skills import SkillExtractor, get_skill_extractor

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_JOBS = DATA_DIR / "jobs.json"
DEFAULT_WEIGHTS = {"semantic": 0.45, "skills": 0.35, "experience": 0.10, "education": 0.10}

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


def education_fit(candidate: str, required: str) -> float:
    """1.0 when the candidate meets the degree requirement, lower per missing level."""
    if not required:
        return 1.0
    if not candidate:
        return 0.5  # degree not detected in the resume
    gap = DEGREE_RANK[required] - DEGREE_RANK[candidate]
    return 1.0 if gap <= 0 else max(0.0, 1.0 - 0.35 * gap)


@dataclass
class MatchResult:
    profile: ResumeProfile
    ranking: pd.DataFrame           # one row per job, sorted by the chosen method
    gaps: dict[str, GapResult]      # job_id -> gap
    recommendations: pd.DataFrame   # skills to learn, aggregated over the top-K jobs
    quality: dict | None = None


class MatchingPipeline:
    def __init__(self, jobs: pd.DataFrame, model_name: str = DEFAULT_MODEL,
                 extractor: SkillExtractor | None = None, semantic: SemanticMatcher | None = None):
        self.jobs = jobs.reset_index(drop=True).copy()
        self.extractor = extractor or get_skill_extractor()

        # Structured job profiles: required vs preferred skills, min. experience and degree.
        req_skills, pref_skills, years, degrees = [], [], [], []
        for desc in self.jobs["description"]:
            req_text, pref_text = split_job_requirements(desc)
            req = self.extractor.extract(req_text)
            pref = [s for s in self.extractor.extract(pref_text) if s not in req]
            req_skills.append(req)
            pref_skills.append(pref)
            years.append(required_experience_years(req_text))
            degrees.append(required_degree(req_text))
        self.jobs["required_skills"] = req_skills
        self.jobs["preferred_skills"] = pref_skills
        self.jobs["min_years"] = years
        self.jobs["required_degree"] = degrees

        self.job_texts = (self.jobs["title"] + ". " + self.jobs["description"]).tolist()
        self.tfidf = TfidfMatcher().fit(self.job_texts)
        self.semantic = semantic or SemanticMatcher(model_name)
        self.job_embeddings = self.semantic.encode_documents(self.job_texts)
        self.gap_analyzer = SkillGapAnalyzer(self.semantic)

    def profile(self, resume_text: str, infer_skills: bool = False) -> ResumeProfile:
        profile = parse_resume(resume_text)
        profile.skills = self.extractor.extract(profile.raw_text)
        if infer_skills:
            profile.inferred_skills = self.extractor.infer(profile.raw_text, self.semantic,
                                                           exclude=set(profile.skills))
        profile.skills_by_category = self.extractor.group_by_category(profile.all_skills)
        return profile

    def match(self, resume_text: str, method: str = "hybrid", top_k: int = 10,
              w_semantic: float | None = None, w_skills: float | None = None,
              w_experience: float | None = None, w_education: float | None = None,
              infer_skills: bool = False) -> MatchResult:
        """method: 'tfidf' (baseline), 'sbert' (semantic only) or 'hybrid'
        (calibrated SBERT + skill coverage + experience fit + education fit)."""
        w = {"semantic": w_semantic, "skills": w_skills, "experience": w_experience, "education": w_education}
        w = {k: DEFAULT_WEIGHTS[k] if v is None else v for k, v in w.items()}

        profile = self.profile(resume_text, infer_skills)
        tfidf_scores = self.tfidf.score(profile.raw_text)
        sbert_scores = self.semantic.score(profile.raw_text, self.job_embeddings)
        sem_norm = calibrate_semantic(sbert_scores)

        gaps, skill_scores, exp_scores, edu_scores = {}, [], [], []
        candidate_skills = profile.all_skills
        for _, job in self.jobs.iterrows():
            gap = self.gap_analyzer.analyze(candidate_skills, job["required_skills"], job["preferred_skills"])
            gaps[job["job_id"]] = gap
            skill_scores.append(gap.skill_score)
            need = job["min_years"]
            exp_scores.append(1.0 if need == 0 else min(1.0, profile.experience_years / need))
            edu_scores.append(education_fit(profile.highest_degree, job["required_degree"]))

        hybrid = []
        for s, k, e, d in zip(sem_norm, skill_scores, exp_scores, edu_scores):
            parts = [(w["semantic"], s), (w["experience"], e), (w["education"], d)]
            if k is not None:  # jobs with no recognised skills are scored without the skill term
                parts.append((w["skills"], k))
            total_w = sum(x for x, _ in parts) or 1.0
            hybrid.append(sum(x * v for x, v in parts) / total_w)

        ranking = self.jobs[["job_id", "title", "company", "category", "location", "required_skills",
                             "preferred_skills", "min_years", "required_degree"]].copy()
        ranking["tfidf_score"] = tfidf_scores
        ranking["sbert_score"] = sbert_scores
        ranking["semantic_score"] = sem_norm  # calibrated 0-1 SBERT score used in the hybrid
        ranking["skill_score"] = [np.nan if k is None else k for k in skill_scores]
        ranking["experience_score"] = exp_scores
        ranking["education_score"] = edu_scores
        ranking["hybrid_score"] = hybrid
        ranking["match_score"] = {"tfidf": tfidf_scores, "sbert": sbert_scores,
                                  "hybrid": np.array(hybrid)}[method]
        for col in ("tfidf_score", "sbert_score", "hybrid_score"):
            ranking[col.replace("_score", "_rank")] = ranking[col].rank(ascending=False, method="first").astype(int)
        ranking = ranking.sort_values("match_score", ascending=False).reset_index(drop=True)

        top = ranking.head(top_k)
        recs = recommend_skills([gaps[j] for j in top["job_id"]], top["title"].tolist(),
                                self.extractor.category_of)
        return MatchResult(profile, ranking, gaps, recs, assess_quality(profile))

    def match_custom_job(self, resume_text: str, title: str, description: str, **kwargs) -> tuple[MatchResult, str]:
        """Score a resume against a job description that is not in the collection.
        The job is added to a copy of the collection so TF-IDF IDF statistics stay meaningful;
        cached embeddings mean only the new job is embedded."""
        extra = pd.DataFrame([{"job_id": "CUSTOM", "title": title or "Custom job", "company": "", "category": "",
                               "location": "", "description": description}])
        cols = ["job_id", "title", "company", "category", "location", "description"]
        temp = MatchingPipeline(pd.concat([self.jobs[cols], extra], ignore_index=True),
                                extractor=self.extractor, semantic=self.semantic)
        return temp.match(resume_text, top_k=1, **kwargs), "CUSTOM"

    def explain(self, resume_text: str, job_id: str, top_n: int = 3) -> list[dict]:
        idx = int(self.jobs.index[self.jobs["job_id"] == job_id][0])
        return self.semantic.explain(resume_text, self.jobs.at[idx, "description"], top_n)

    def keyword_overlap(self, resume_text: str, job_id: str, n: int = 10) -> list[str]:
        idx = int(self.jobs.index[self.jobs["job_id"] == job_id][0])
        return self.tfidf.top_terms(resume_text, idx, n)


# ----------------------------------------------------------------------------- serialisation

def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def gap_to_dict(gap: GapResult) -> dict:
    d = asdict(gap)
    d["skill_score"] = _clean(gap.skill_score) if gap.skill_score is not None else None
    return d


def job_row_to_dict(row: pd.Series, gap: GapResult, rank: int) -> dict:
    return {
        "rank": rank, "job_id": row["job_id"], "title": row["title"], "company": row["company"],
        "category": row["category"], "location": row["location"],
        "required_skills": list(row["required_skills"]), "preferred_skills": list(row["preferred_skills"]),
        "min_years": _clean(row["min_years"]), "required_degree": row["required_degree"],
        "scores": {k: _clean(row[f"{k}_score"]) for k in
                   ("match", "hybrid", "semantic", "sbert", "tfidf", "skill", "experience", "education")},
        "ranks": {k: int(row[f"{k}_rank"]) for k in ("tfidf", "sbert", "hybrid")},
        "gap": gap_to_dict(gap),
    }


def result_to_dict(result: MatchResult, top_k: int) -> dict:
    p = result.profile
    ranking = result.ranking
    rho = ranking["tfidf_score"].corr(ranking["sbert_score"], method="spearman")
    return {
        "profile": {
            "name": p.name, "email": p.email, "phone": p.phone, "links": p.links,
            "highest_degree": p.highest_degree, "experience_years": p.experience_years,
            "education": p.education, "skills": p.skills, "inferred_skills": p.inferred_skills,
            "skills_by_category": p.skills_by_category, "sections": p.sections, "raw_text": p.raw_text,
        },
        "quality": result.quality,
        "matches": [job_row_to_dict(row, result.gaps[row["job_id"]], i + 1)
                    for i, (_, row) in enumerate(ranking.head(top_k).iterrows())],
        "comparison": {
            "spearman": _clean(rho),
            "rows": [{"job_id": r["job_id"], "title": r["title"], "company": r["company"],
                      "tfidf_rank": int(r["tfidf_rank"]), "sbert_rank": int(r["sbert_rank"]),
                      "hybrid_rank": int(r["hybrid_rank"]), "tfidf_score": _clean(r["tfidf_score"]),
                      "sbert_score": _clean(r["sbert_score"]), "hybrid_score": _clean(r["hybrid_score"])}
                     for _, r in ranking.sort_values("hybrid_rank").iterrows()],
        },
        "recommendations": [{"skill": r["Skill"], "category": r["Category"], "priority": _clean(r["Priority"]),
                             "needed_by": int(r["Needed by (top jobs)"]), "jobs": r["Jobs"].split(", "),
                             "advice": r["How to improve"], "related_to": r["Related skill you have"],
                             "phase": r["Phase"]}
                            for _, r in result.recommendations.iterrows()],
    }
