"""NLP preprocessing: cleaning, tokenization, stop-word removal and lemmatization (spaCy)."""

from __future__ import annotations

import re
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

_URL_RE = re.compile(r"(?:https?://|www\.)\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# keep characters that matter in tech terms: c++, c#, .net, node.js
_KEEP_RE = re.compile(r"[^a-z0-9+#.\s]")


@lru_cache(maxsize=1)
def get_nlp():
    """Load spaCy English pipeline (only what we need). Falls back to a blank
    tokenizer if the model isn't downloaded, so the app still runs."""
    import spacy
    try:
        return spacy.load("en_core_web_sm", disable=["parser", "ner"])
    except OSError:
        return spacy.blank("en")


def clean_text(text: str) -> str:
    text = text.lower()
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _KEEP_RE.sub(" ", text)
    text = re.sub(r"(?<![a-z0-9])\.|\.(?![a-z0-9])", " ", text)  # drop sentence dots, keep '.net'
    return re.sub(r"\s+", " ", text).strip()


def preprocess(text: str, lemmatize: bool = True) -> str:
    """Clean -> tokenize -> remove stop words -> lemmatize. Used for the TF-IDF baseline."""
    cleaned = clean_text(text)
    nlp = get_nlp()
    doc = nlp(cleaned[:1_000_000])
    has_lemmas = lemmatize and nlp.has_pipe("lemmatizer")
    tokens = []
    for tok in doc:
        word = tok.text
        if word in ENGLISH_STOP_WORDS or len(word) < 2 and word not in {"c", "r"}:
            continue
        if word.isdigit():
            continue
        lemma = tok.lemma_.lower() if has_lemmas and tok.lemma_ else word
        tokens.append(lemma if re.fullmatch(r"[a-z]+", word) else word)
    return " ".join(tokens)


def split_sentences(text: str, min_words: int = 3) -> list[str]:
    """Split text into sentence-like units (lines / bullets / sentences)."""
    parts = []
    for line in text.splitlines():
        line = line.strip(" •-*\t")
        if not line:
            continue
        for piece in re.split(r"(?<=[.!?;])\s+(?=[A-Z])", line):
            if len(piece.split()) >= min_words:
                parts.append(piece.strip())
    return parts


def chunk_text(text: str, max_words: int = 120) -> list[str]:
    """Group sentences into chunks of about max_words, so long documents fit
    the Transformer's input limit (MiniLM truncates at 256 word pieces)."""
    chunks, current, count = [], [], 0
    for sent in split_sentences(text, min_words=1):
        n = len(sent.split())
        if current and count + n > max_words:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += n
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]
