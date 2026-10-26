"""Skill-gap analysis and skill recommendations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

CATEGORY_ADVICE = {
    "Programming Languages": "Practice the language with small exercises (e.g. LeetCode/HackerRank) and build one complete project in it.",
    "Web Development": "Build and deploy a small full-stack app that uses it, and put the code on GitHub.",
    "Mobile Development": "Publish a simple app (e.g. a to-do or notes app) that uses it.",
    "Databases": "Design a schema for a sample project and practise queries, indexing and joins.",
    "Cloud & DevOps": "Deploy one of your projects with it; free tiers and official tutorials are enough to start.",
    "Data Science & AI": "Complete a hands-on course and do an end-to-end project on a public dataset (e.g. from Kaggle).",
    "BI & Analytics Tools": "Build a dashboard on a public dataset and add it to your portfolio.",
    "Testing & Quality": "Add tests with it to one of your existing projects.",
    "Security": "Study the fundamentals and practise in legal labs (e.g. TryHackMe, OWASP Juice Shop).",
    "Networking & IT": "Set up a home lab or use a simulator (e.g. Packet Tracer) and consider an entry-level certification.",
    "Design": "Redesign an existing app screen and present it as a case study.",
    "Business & Management": "Take a short course and apply it in a project or volunteer role you can describe on your resume.",
    "Soft Skills": "Show it with concrete examples on your resume (team projects, presentations, leadership roles).",
    "Software Engineering": "Study the concept and refactor one of your projects to demonstrate it.",
}


@dataclass
class GapResult:
    matched_required: list[str] = field(default_factory=list)
    matched_preferred: list[str] = field(default_factory=list)
    partial: list[dict] = field(default_factory=list)  # {"job_skill", "candidate_skill", "similarity", "type"}
    missing_required: list[str] = field(default_factory=list)
    missing_preferred: list[str] = field(default_factory=list)
    skill_score: float | None = None  # None when the job lists no recognised skills

    @property
    def matched(self) -> list[str]:
        return self.matched_required + self.matched_preferred

    @property
    def missing(self) -> list[str]:
        return self.missing_required + self.missing_preferred


class SkillGapAnalyzer:
    """Compares candidate skills with a job's required / preferred skills.

    1. Exact match on canonical skill names (after alias normalisation).
    2. Semantic partial match: a missing job skill counts as 'partially covered'
       if one of the candidate's skills is semantically close to it
       (SBERT cosine >= threshold), e.g. TensorFlow ~ PyTorch.
    """

    def __init__(self, semantic_matcher=None, threshold: float = 0.65,
                 required_weight: float = 0.75, partial_credit: float = 0.5):
        self.semantic = semantic_matcher
        self.threshold = threshold
        self.required_weight = required_weight
        self.partial_credit = partial_credit

    def _closest(self, missing: list[str], candidate: list[str]) -> dict[str, tuple[str, float]]:
        if not self.semantic or not missing or not candidate:
            return {}
        sims = self.semantic.encode_short(missing) @ self.semantic.encode_short(candidate).T
        out = {}
        for i, skill in enumerate(missing):
            j = int(sims[i].argmax())
            if sims[i, j] >= self.threshold:
                out[skill] = (candidate[j], float(sims[i, j]))
        return out

    def analyze(self, candidate_skills: list[str], required: list[str], preferred: list[str]) -> GapResult:
        cand = set(candidate_skills)
        res = GapResult()
        res.matched_required = sorted(s for s in required if s in cand)
        res.matched_preferred = sorted(s for s in preferred if s in cand)
        miss_req = sorted(s for s in required if s not in cand)
        miss_pref = sorted(s for s in preferred if s not in cand)

        close = self._closest(miss_req + miss_pref, sorted(cand))
        for skill in miss_req + miss_pref:
            if skill in close:
                res.partial.append({"job_skill": skill, "candidate_skill": close[skill][0],
                                    "similarity": round(close[skill][1], 3),
                                    "type": "required" if skill in miss_req else "preferred"})
        res.missing_required = [s for s in miss_req if s not in close]
        res.missing_preferred = [s for s in miss_pref if s not in close]

        def coverage(total, matched, part_type):
            if not total:
                return None
            part = sum(1 for p in res.partial if p["type"] == part_type)
            return (len(matched) + self.partial_credit * part) / len(total)

        req_cov = coverage(required, res.matched_required, "required")
        pref_cov = coverage(preferred, res.matched_preferred, "preferred")
        if req_cov is not None and pref_cov is not None:
            res.skill_score = self.required_weight * req_cov + (1 - self.required_weight) * pref_cov
        else:
            res.skill_score = req_cov if req_cov is not None else pref_cov
        return res


def recommend_skills(gaps: list[GapResult], job_titles: list[str], category_of: dict[str, str],
                     top_n: int = 10) -> pd.DataFrame:
    """Aggregate gaps across the top-ranked jobs and rank skills to learn.
    Priority = 2 x (#jobs requiring it) + 1 x (#jobs preferring it);
    partially covered skills get half weight because the candidate has a related skill."""
    priority = defaultdict(float)
    jobs_for = defaultdict(list)
    related = {}
    for gap, title in zip(gaps, job_titles):
        for s in gap.missing_required:
            priority[s] += 2
            jobs_for[s].append(title)
        for s in gap.missing_preferred:
            priority[s] += 1
            jobs_for[s].append(title)
        for p in gap.partial:
            priority[p["job_skill"]] += 1 if p["type"] == "required" else 0.5
            jobs_for[p["job_skill"]].append(title)
            related[p["job_skill"]] = p["candidate_skill"]
    rows = []
    for skill, score in sorted(priority.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]:
        category = category_of.get(skill, "Other")
        advice = CATEGORY_ADVICE.get(category, "Learn the basics and apply it in a project.")
        if skill in related:
            advice = f"You already know {related[skill]}, so {skill} should be quick to pick up. " + advice
        rows.append({"Skill": skill, "Category": category, "Priority": score,
                     "Needed by (top jobs)": len(set(jobs_for[skill])),
                     "Jobs": ", ".join(sorted(set(jobs_for[skill]))), "How to improve": advice})
    return pd.DataFrame(rows)
