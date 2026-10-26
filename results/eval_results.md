# Evaluation results (2026-10-26 09:24)

Model: `sentence-transformers/all-MiniLM-L6-v2` | Jobs: 30 | Dataset: hand-labelled sample (8 resumes)

## Skill extraction

| Metric | Precision | Recall | F1 |
|---|---|---|---|
| Micro | 0.990 | 0.933 | 0.961 |
| Macro | 0.993 | 0.941 | 0.966 |

## Job ranking

Queries (resumes): 8

| Method | MRR | P@1 | Recall@1 | nDCG@1 | P@3 | Recall@3 | nDCG@3 | P@5 | Recall@5 | nDCG@5 |
|---|---|---|---|---|---|---|---|---|---|---|
| TF-IDF + Cosine (baseline) | 1.000 | 1.000 | 0.542 | 1.000 | 0.625 | 0.938 | 0.952 | 0.400 | 1.000 | 0.985 |
| SBERT + Cosine (proposed) | 1.000 | 1.000 | 0.542 | 1.000 | 0.625 | 0.938 | 0.952 | 0.400 | 1.000 | 0.981 |
| Hybrid: SBERT + Skills + Experience | 1.000 | 1.000 | 0.542 | 1.000 | 0.667 | 1.000 | 0.990 | 0.400 | 1.000 | 0.990 |
