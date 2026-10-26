"""Matching models.

* TfidfMatcher    - baseline: TF-IDF vectors + cosine similarity (keyword / vector-space).
* SemanticMatcher - proposed: pretrained Sentence Transformer (SBERT) embeddings + cosine similarity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .preprocess import chunk_text, preprocess, split_sentences

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
AVAILABLE_MODELS = {
    "all-MiniLM-L6-v2 (fast)": "sentence-transformers/all-MiniLM-L6-v2",
    "all-mpnet-base-v2 (more accurate, slower)": "sentence-transformers/all-mpnet-base-v2",
}
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "embeddings"


class TfidfMatcher:
    """Baseline: bag-of-words TF-IDF (unigrams + bigrams) and cosine similarity."""

    def __init__(self, ngram_range=(1, 2), min_df=1, sublinear_tf=True):
        self.vectorizer = TfidfVectorizer(ngram_range=ngram_range, min_df=min_df,
                                          sublinear_tf=sublinear_tf, token_pattern=r"(?u)[\w+#.]+")
        self.job_matrix = None

    def fit(self, job_texts: list[str]) -> "TfidfMatcher":
        self.job_matrix = self.vectorizer.fit_transform([preprocess(t) for t in job_texts])
        return self

    def score(self, resume_text: str) -> np.ndarray:
        vec = self.vectorizer.transform([preprocess(resume_text)])
        return cosine_similarity(vec, self.job_matrix).ravel()

    def top_terms(self, resume_text: str, job_index: int, n: int = 10) -> list[str]:
        """Terms shared by the resume and a job, ranked by their TF-IDF contribution."""
        vec = self.vectorizer.transform([preprocess(resume_text)])
        contrib = vec.multiply(self.job_matrix[job_index]).toarray().ravel()
        terms = self.vectorizer.get_feature_names_out()
        idx = contrib.argsort()[::-1][:n]
        return [terms[i] for i in idx if contrib[i] > 0]


class SemanticMatcher:
    """Proposed approach: Sentence-BERT document embeddings.

    Long documents are split into ~120-word chunks (the model truncates long
    inputs), each chunk is embedded, and the chunk embeddings are averaged
    and L2-normalised into a single document vector."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str | None = None):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.job_embeddings: np.ndarray | None = None
        self._short_cache: dict[str, np.ndarray] = {}

    # -- encoding -----------------------------------------------------------------
    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)

    def encode_document(self, text: str) -> np.ndarray:
        chunks = chunk_text(text)
        emb = self.encode(chunks).mean(axis=0)
        return emb / (np.linalg.norm(emb) + 1e-12)

    def encode_documents(self, texts: list[str], use_cache: bool = True) -> np.ndarray:
        key = hashlib.sha1((self.model_name + "\x00".join(texts)).encode("utf-8")).hexdigest()[:16]
        path = CACHE_DIR / f"{key}.npy"
        if use_cache and path.exists():
            return np.load(path)
        all_chunks, owners = [], []
        for i, t in enumerate(texts):
            chunks = chunk_text(t)
            all_chunks.extend(chunks)
            owners.extend([i] * len(chunks))
        chunk_emb = self.encode(all_chunks)
        owners = np.array(owners)
        docs = np.vstack([chunk_emb[owners == i].mean(axis=0) for i in range(len(texts))])
        docs /= np.linalg.norm(docs, axis=1, keepdims=True) + 1e-12
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            np.save(path, docs)
        return docs

    def encode_short(self, phrases: list[str]) -> np.ndarray:
        """Embeddings for short phrases (skill names), memoised."""
        missing = [p for p in dict.fromkeys(phrases) if p not in self._short_cache]
        if missing:
            for p, e in zip(missing, self.encode(missing)):
                self._short_cache[p] = e
        return np.vstack([self._short_cache[p] for p in phrases]) if phrases else np.zeros((0, 1))

    # -- matching -----------------------------------------------------------------
    def fit(self, job_texts: list[str]) -> "SemanticMatcher":
        self.job_embeddings = self.encode_documents(job_texts)
        return self

    def score(self, resume_text: str) -> np.ndarray:
        return self.job_embeddings @ self.encode_document(resume_text)

    def explain(self, resume_text: str, job_text: str, top_n: int = 3) -> list[dict]:
        """Explainability: the job requirement sentences that best match resume
        sentences, with the matching resume evidence and similarity."""
        r_sents = split_sentences(resume_text)
        j_sents = split_sentences(job_text, min_words=4)
        if not r_sents or not j_sents:
            return []
        sims = self.encode(j_sents) @ self.encode(r_sents).T
        best = sims.argmax(axis=1)
        order = sims.max(axis=1).argsort()[::-1][:top_n]
        return [{"job_requirement": j_sents[j], "resume_evidence": r_sents[best[j]],
                 "similarity": float(sims[j, best[j]])} for j in order]


def calibrate_semantic(score: np.ndarray | float, low: float = 0.15, high: float = 0.70):
    """Map raw SBERT cosine (which in practice lies roughly in 0.1-0.75 for
    resume/job pairs) to 0-1 so it can be combined with the skill score."""
    return np.clip((np.asarray(score) - low) / (high - low), 0.0, 1.0)
