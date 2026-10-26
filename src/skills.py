"""Dictionary-based skill extraction with spaCy PhraseMatcher.

Every skill in data/skills.json has a canonical name and a list of aliases
(e.g. "Machine Learning": ["machine learning", "ml"]). Matching is done on
lower-cased tokens, so "ReactJS", "react.js" and "React" all map to "React".
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

DEFAULT_TAXONOMY = Path(__file__).resolve().parent.parent / "data" / "skills.json"


class SkillExtractor:
    def __init__(self, taxonomy_path: str | Path = DEFAULT_TAXONOMY):
        import spacy
        from spacy.matcher import PhraseMatcher

        with open(taxonomy_path, encoding="utf-8") as f:
            taxonomy = json.load(f)

        self.category_of: dict[str, str] = {}
        self.aliases: dict[str, list[str]] = {}
        for category, skills in taxonomy.items():
            for canonical, aliases in skills.items():
                self.category_of[canonical] = category
                names = {a.lower() for a in aliases}
                if len(canonical) > 2:  # "C", "R", "Go" are too ambiguous to match on their own
                    names.add(canonical.lower())
                self.aliases[canonical] = sorted(names)

        # A blank pipeline is enough: we only need the tokenizer, and it keeps matching fast.
        self.nlp = spacy.blank("en")
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        for canonical, aliases in self.aliases.items():
            self.matcher.add(canonical, [self.nlp.make_doc(a) for a in aliases])

    @property
    def all_skills(self) -> list[str]:
        return sorted(self.category_of)

    def extract(self, text: str) -> list[str]:
        """Return the sorted list of canonical skills mentioned in text."""
        if not text:
            return []
        return sorted({span.label_ for span in self._spans(text)})

    def extract_with_counts(self, text: str) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for span in self._spans(text):
            counts[span.label_] += 1
        return dict(counts)

    def _spans(self, text: str):
        """Matched spans, keeping only the longest of overlapping matches so that
        "SQL Server" does not also count as "SQL", nor "ASP.NET MVC" as "MVC"."""
        from spacy.util import filter_spans
        return filter_spans(self.matcher(self.nlp.make_doc(text), as_spans=True))

    def infer(self, text: str, semantic, exclude: set[str] | None = None,
              threshold: float = 0.80, max_phrases: int = 400) -> list[dict]:
        """Semantic skill inference for skills described in other words
        (e.g. "neural nets" -> Deep Learning, "statistical modelling" -> Statistics).

        Candidate phrases are spaCy noun chunks plus short comma-separated items;
        each is embedded with the Sentence Transformer and compared with every
        skill alias. A skill is inferred when the best similarity >= threshold."""
        import numpy as np
        from .preprocess import get_parser_nlp

        exclude = exclude or set()
        phrases: dict[str, None] = {}
        doc = get_parser_nlp()(text[:100_000])
        for chunk in doc.noun_chunks:
            words = [t.text.lower() for t in chunk if not (t.is_stop or t.is_punct or t.like_num)]
            if 2 <= len(words) <= 4:
                phrases[" ".join(words)] = None
        for line in text.splitlines():
            for piece in re.split(r"[,;|•()/]| and ", line):
                words = piece.strip(" .:-").lower().split()
                if 2 <= len(words) <= 4:
                    phrases[" ".join(words)] = None
        # Single words are left to the dictionary: on their own they are too ambiguous
        # for embeddings ("experience" ~ "user experience", "jun" ~ "junit").
        candidates = [p for p in phrases if len(p) > 2 and not self.matcher(self.nlp.make_doc(p))][:max_phrases]
        if not candidates:
            return []

        alias_list = [(canonical, alias) for canonical, aliases in self.aliases.items()
                      for alias in aliases if len(alias) > 3]
        sims = semantic.encode_short(candidates) @ semantic.encode_short([a for _, a in alias_list]).T
        best: dict[str, dict] = {}
        for i, phrase in enumerate(candidates):
            j = int(np.argmax(sims[i]))
            score = float(sims[i, j])
            canonical = alias_list[j][0]
            if score >= threshold and canonical not in exclude:
                if canonical not in best or score > best[canonical]["similarity"]:
                    best[canonical] = {"skill": canonical, "evidence": phrase, "similarity": round(score, 3),
                                       "category": self.category_of[canonical]}
        return sorted(best.values(), key=lambda d: -d["similarity"])

    def group_by_category(self, skills: list[str]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for s in skills:
            grouped[self.category_of.get(s, "Other")].append(s)
        return {k: sorted(v) for k, v in sorted(grouped.items())}


@lru_cache(maxsize=1)
def get_skill_extractor() -> SkillExtractor:
    return SkillExtractor()
