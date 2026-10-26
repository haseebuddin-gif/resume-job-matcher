"""Experiments: skill-extraction quality and TF-IDF vs SBERT vs Hybrid ranking quality.

Usage
-----
# 1) Hand-labelled sample set shipped with the project (data/eval/annotations.json)
python evaluate.py

# 2) Public Kaggle resume dataset (relevance = resume category == job category)
#    e.g. "UpdatedResumeDataSet.csv" (columns: Category, Resume)
python evaluate.py --kaggle-resumes path/to/UpdatedResumeDataSet.csv --per-category 20

# Use a larger / different job set or model
python evaluate.py --jobs path/to/jobs.csv --model sentence-transformers/all-mpnet-base-v2
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.evaluation import extraction_scores, ranking_scores
from src.matcher import AVAILABLE_MODELS, DEFAULT_MODEL
from src.pipeline import DEFAULT_JOBS, MatchingPipeline, load_jobs

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
METHODS = {"tfidf": "TF-IDF + Cosine (baseline)", "sbert": "SBERT + Cosine (proposed)",
           "hybrid": "Hybrid: SBERT + Skills + Experience + Education"}


def load_annotated(path: Path) -> tuple[list[str], list[set], list[set], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    texts, gold_skills, relevant, names = [], [], [], []
    for r in data["resumes"]:
        texts.append((ROOT / "data" / "sample_resumes" / r["file"]).read_text(encoding="utf-8"))
        gold_skills.append(set(r["gold_skills"]))
        relevant.append(set(r["relevant_jobs"]))
        names.append(r["file"])
    return texts, gold_skills, relevant, names


def load_kaggle(path: Path, jobs: pd.DataFrame, per_category: int, seed: int = 42):
    df = pd.read_csv(path)
    text_col = next(c for c in ("Resume", "Resume_str", "resume", "text") if c in df.columns)
    cat_col = next(c for c in ("Category", "category") if c in df.columns)
    job_cats = {c.lower(): set(jobs.loc[jobs["category"].str.lower() == c.lower(), "job_id"])
                for c in jobs["category"].unique() if c}
    df = df[df[cat_col].str.lower().isin(job_cats)].drop_duplicates(subset=[text_col])
    df = df.groupby(cat_col, group_keys=False).apply(
        lambda g: g.sample(min(len(g), per_category), random_state=seed))
    texts = df[text_col].astype(str).tolist()
    relevant = [job_cats[c.lower()] for c in df[cat_col]]
    return texts, relevant, df[cat_col].tolist()


def evaluate_annotated(pipe: MatchingPipeline, annotations: Path = ROOT / "data" / "eval" / "annotations.json") -> dict:
    """Full experiment on the hand-labelled set: extraction (with an ablation of
    semantic skill inference) and ranking for all three methods."""
    texts, gold, relevant, names = load_annotated(annotations)
    preds = [set(pipe.extractor.extract(t)) for t in texts]
    inferred = [{d["skill"] for d in pipe.extractor.infer(t, pipe.semantic, exclude=p)}
                for t, p in zip(texts, preds)]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": pipe.semantic.model_name,
        "n_jobs": len(pipe.jobs), "dataset": f"hand-labelled sample ({len(texts)} resumes)",
        "extraction": extraction_scores(preds, gold),
        "extraction_ablation": {
            "Dictionary (PhraseMatcher)": extraction_scores(preds, gold),
            "Dictionary + semantic inference": extraction_scores([p | i for p, i in zip(preds, inferred)], gold),
        },
        "extraction_per_resume": {n: {"missed": sorted(g - p), "extra": sorted(p - g)}
                                  for n, p, g in zip(names, preds, gold)},
        "ranking": run_ranking(pipe, texts, relevant),
    }


def run_ranking(pipe: MatchingPipeline, texts: list[str], relevant: list[set]) -> dict:
    rankings = {m: [] for m in METHODS}
    for text in texts:
        result = pipe.match(text, method="hybrid", top_k=5)
        for m in METHODS:
            rankings[m].append(result.ranking.sort_values(f"{m}_score", ascending=False)["job_id"].tolist())
    return {m: ranking_scores(rankings[m], relevant) for m in METHODS}


def to_markdown(results: dict) -> str:
    lines = [f"# Evaluation results ({results['timestamp']})", "",
             f"Model: `{results['model']}` | Jobs: {results['n_jobs']} | Dataset: {results['dataset']}", ""]
    if "extraction" in results:
        e = results["extraction"]
        lines += ["## Skill extraction", "", "| Metric | Precision | Recall | F1 |", "|---|---|---|---|",
                  f"| Micro | {e['micro_precision']:.3f} | {e['micro_recall']:.3f} | {e['micro_f1']:.3f} |",
                  f"| Macro | {e['macro_precision']:.3f} | {e['macro_recall']:.3f} | {e['macro_f1']:.3f} |", ""]
    if "extraction_ablation" in results:
        lines += ["### Ablation: semantic skill inference (micro-averaged)", "",
                  "| Extractor | Precision | Recall | F1 |", "|---|---|---|---|"]
        for name, e in results["extraction_ablation"].items():
            lines.append(f"| {name} | {e['micro_precision']:.3f} | {e['micro_recall']:.3f} | {e['micro_f1']:.3f} |")
        lines.append("")
    r = results["ranking"]
    keys = [k for k in next(iter(r.values())) if k != "queries"]
    lines += ["## Job ranking", "", f"Queries (resumes): {next(iter(r.values()))['queries']}", "",
              "| Method | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for m, scores in r.items():
        lines.append(f"| {METHODS[m]} | " + " | ".join(f"{scores[k]:.3f}" for k in keys) + " |")
    for model, mr in results.get("model_comparison", {}).items():
        lines += ["", f"### Ranking with `{model}`", "", "| Method | " + " | ".join(keys) + " |",
                  "|---" * (len(keys) + 1) + "|"]
        for m, scores in mr.items():
            lines.append(f"| {METHODS[m]} | " + " | ".join(f"{scores[k]:.3f}" for k in keys) + " |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", default=str(DEFAULT_JOBS))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--annotations", default=str(ROOT / "data" / "eval" / "annotations.json"))
    ap.add_argument("--kaggle-resumes", help="CSV with resume text + Category columns")
    ap.add_argument("--per-category", type=int, default=20)
    ap.add_argument("--compare-models", action="store_true",
                    help="also rank with every model in AVAILABLE_MODELS (slower)")
    args = ap.parse_args()

    jobs = load_jobs(args.jobs)
    print(f"Loading model {args.model} and indexing {len(jobs)} jobs ...")
    pipe = MatchingPipeline(jobs, model_name=args.model)

    if args.kaggle_resumes:
        texts, relevant, cats = load_kaggle(Path(args.kaggle_resumes), jobs, args.per_category)
        print(f"Ranking {len(texts)} resumes ...")
        results = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": args.model,
                   "n_jobs": len(jobs),
                   "dataset": f"{Path(args.kaggle_resumes).name} ({len(texts)} resumes, {len(set(cats))} categories)",
                   "ranking": run_ranking(pipe, texts, relevant)}
    else:
        texts, _, relevant, _ = load_annotated(Path(args.annotations))
        print(f"Evaluating {len(texts)} annotated resumes ...")
        results = evaluate_annotated(pipe, Path(args.annotations))

    if args.compare_models:
        results["model_comparison"] = {}
        for name in AVAILABLE_MODELS.values():
            print(f"Ranking with {name} ...")
            other = pipe if name == args.model else MatchingPipeline(jobs, model_name=name)
            results["model_comparison"][name] = run_ranking(other, texts, relevant)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "eval_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    md = to_markdown(results)
    (RESULTS_DIR / "eval_results.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    if "extraction_per_resume" in results:
        print("Extraction errors per resume (useful for the report's error analysis):")
        for n, d in results["extraction_per_resume"].items():
            print(f"  {n}: missed={d['missed']} extra={d['extra']}")
    print(f"\nSaved to {RESULTS_DIR / 'eval_results.md'}")


if __name__ == "__main__":
    main()
