"""Resume quality / ATS-readiness checks with actionable feedback."""

from __future__ import annotations

import re

from .parser import ResumeProfile

ACTION_VERBS = {
    "achieved", "analysed", "analyzed", "architected", "automated", "built", "collaborated", "conducted",
    "configured", "coordinated", "created", "decreased", "delivered", "deployed", "designed", "developed",
    "drove", "enhanced", "established", "evaluated", "executed", "generated", "handled", "implemented",
    "improved", "increased", "integrated", "introduced", "launched", "led", "maintained", "managed",
    "mentored", "migrated", "optimised", "optimized", "organised", "organized", "performed", "planned",
    "presented", "produced", "reduced", "refactored", "resolved", "scaled", "set", "streamlined",
    "supported", "trained", "wrote", "gathered", "documented", "converted", "administered", "screened",
    "helped", "tested", "created", "owned", "spearheaded", "negotiated", "researched", "migrated",
}


def _bullets(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln.lstrip("•-*· ").strip() for ln in lines if re.match(r"^[•\-*·]\s*\w", ln)]


def assess_quality(profile: ResumeProfile) -> dict:
    """Score 0-100 from weighted checks. Each check returns pass/fail and a tip."""
    text = profile.raw_text
    words = len(text.split())
    bullets = _bullets(text)
    quantified = [b for b in bullets if re.search(r"\d+\s*%|\d{2,}|\b\d+x\b|\$\s?\d", b)]
    action = [b for b in bullets if b.split()[0].lower().strip(",.") in ACTION_VERBS] if bullets else []
    s = profile.sections

    checks = [
        ("email", "Email address", 8, bool(profile.email), "Add a professional email address at the top."),
        ("phone", "Phone number", 5, bool(profile.phone), "Add a phone number so recruiters can reach you."),
        ("links", "LinkedIn / GitHub / portfolio link", 5, bool(profile.links),
         "Add a LinkedIn or GitHub link; for technical roles a GitHub profile adds credibility."),
        ("summary", "Professional summary", 6, "summary" in s,
         "Add a 2-3 line summary that states your role, years of experience and main strengths."),
        ("skills", "Dedicated skills section", 10, "skills" in s,
         "Add a 'Skills' section; applicant tracking systems look for it."),
        ("experience", "Experience section", 12, "experience" in s,
         "Add work experience, internships or freelance work with dates."),
        ("education", "Education section", 8, "education" in s, "Add your degree, institution and year."),
        ("projects", "Projects section", 6, "projects" in s,
         "Add 2-3 projects with the technologies used; this matters most for fresh graduates."),
        ("length", "Length between 250 and 1000 words", 8, 250 <= words <= 1000,
         f"Your resume has {words} words. Aim for 250-1000 words (1-2 pages)."),
        ("skill_count", "At least 8 recognised skills", 10, len(profile.skills) >= 8,
         f"Only {len(profile.skills)} skills were recognised. List tools and technologies explicitly."),
        ("quantified", "Achievements are quantified", 12, len(quantified) >= 2,
         "Add numbers to your achievements (e.g. 'reduced load time by 40%', 'served 10k users')."),
        ("action_verbs", "Bullets start with action verbs", 10,
         bool(bullets) and len(action) / len(bullets) >= 0.5,
         "Start bullet points with strong verbs such as Built, Led, Improved, Automated."),
    ]
    total = sum(w for _, _, w, _, _ in checks)
    score = round(100 * sum(w for _, _, w, ok, _ in checks if ok) / total)
    return {
        "score": score,
        "grade": "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Needs work",
        "stats": {"words": words, "bullets": len(bullets), "quantified_bullets": len(quantified),
                  "action_verb_bullets": len(action)},
        "checks": [{"id": cid, "label": label, "weight": w, "passed": ok, "tip": None if ok else tip}
                   for cid, label, w, ok, tip in checks],
    }
