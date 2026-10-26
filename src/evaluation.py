"""Evaluation metrics: extraction (Precision / Recall / F1) and ranking (P@K, Recall@K, MRR, nDCG@K)."""

from __future__ import annotations

import math


def prf(predicted: set, gold: set) -> tuple[float, float, float]:
    tp = len(predicted & gold)
    p = tp / len(predicted) if predicted else 0.0
    r = tp / len(gold) if gold else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def extraction_scores(predictions: list[set], golds: list[set]) -> dict:
    """Micro-averaged (pooled TP/FP/FN) and macro-averaged (mean per document) P/R/F1."""
    tp = sum(len(p & g) for p, g in zip(predictions, golds))
    n_pred = sum(len(p) for p in predictions)
    n_gold = sum(len(g) for g in golds)
    micro_p = tp / n_pred if n_pred else 0.0
    micro_r = tp / n_gold if n_gold else 0.0
    micro_f = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    per_doc = [prf(p, g) for p, g in zip(predictions, golds)]
    n = len(per_doc) or 1
    return {
        "micro_precision": micro_p, "micro_recall": micro_r, "micro_f1": micro_f,
        "macro_precision": sum(x[0] for x in per_doc) / n,
        "macro_recall": sum(x[1] for x in per_doc) / n,
        "macro_f1": sum(x[2] for x in per_doc) / n,
    }


def precision_at_k(ranked: list, relevant: set, k: int) -> float:
    return sum(1 for item in ranked[:k] if item in relevant) / k


def recall_at_k(ranked: list, relevant: set, k: int) -> float:
    return sum(1 for item in ranked[:k] if item in relevant) / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked: list, relevant: set) -> float:
    for i, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list, relevant: set, k: int) -> float:
    dcg = sum(1.0 / math.log2(i + 1) for i, item in enumerate(ranked[:k], start=1) if item in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def ranking_scores(rankings: list[list], relevants: list[set], ks=(1, 3, 5)) -> dict:
    """Mean ranking metrics over all queries (resumes) that have at least one relevant job."""
    pairs = [(r, rel) for r, rel in zip(rankings, relevants) if rel]
    n = len(pairs) or 1
    out = {"queries": len(pairs), "MRR": sum(reciprocal_rank(r, rel) for r, rel in pairs) / n}
    for k in ks:
        out[f"P@{k}"] = sum(precision_at_k(r, rel, k) for r, rel in pairs) / n
        out[f"Recall@{k}"] = sum(recall_at_k(r, rel, k) for r, rel in pairs) / n
        out[f"nDCG@{k}"] = sum(ndcg_at_k(r, rel, k) for r, rel in pairs) / n
    return out
