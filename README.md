# AI-Based Resume–Job Matching and Skill Gap Analysis Using NLP

Upload a resume and get a **ranked list of suitable jobs** with a **match score, matched skills,
missing skills and recommended areas for improvement**. The project also compares a traditional
**TF-IDF + Cosine Similarity** baseline with **Sentence Transformer (SBERT)** semantic matching.

Everything runs locally with open-source models. No paid AI API is needed.

## Features

| Objective (from proposal) | Where it is implemented |
|---|---|
| Extract skills, education, experience, projects from resumes | `src/parser.py` (sections, contact, education, experience years), `src/skills.py` (skills) |
| Extract required and preferred skills from job descriptions | `parser.split_job_requirements` + `SkillExtractor` |
| Semantic representations with pretrained Transformers | `src/matcher.py` → `SemanticMatcher` (all-MiniLM-L6-v2 / all-mpnet-base-v2) |
| Similarity scores and job ranking | `src/pipeline.py` → `MatchingPipeline.match` |
| Missing skills and a personalised skill-gap report | `src/gap.py` → `SkillGapAnalyzer` |
| Skill recommendations | `src/gap.py` → `recommend_skills` |
| TF-IDF vs Sentence Transformer comparison | `TfidfMatcher` vs `SemanticMatcher`, `evaluate.py`, *TF-IDF vs SBERT* tab in the app |
| Explainable results | matched/missing skills, "why this match" sentence evidence, shared TF-IDF keywords |

## Quick start (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU build, smaller download
pip install -r requirements.txt
python -m spacy download en_core_web_sm

streamlit run app.py          # web app at http://localhost:8501
python evaluate.py            # experiments -> results/eval_results.md
```

The first run downloads the Sentence Transformer model (~90 MB) from Hugging Face. After that it works offline.

## How it works

```
Resume (PDF/DOCX/TXT)                        Job descriptions (JSON/CSV)
        │                                               │
  text extraction (pdfplumber / python-docx)            │
  section split · contact · education · experience     split into required / preferred
        │                                               │
  skill extraction (spaCy PhraseMatcher + taxonomy) ────┤
        │                                               │
        ├── TF-IDF (spaCy lemmatised, 1-2 grams) ── cosine ──► baseline ranking
        ├── SBERT embeddings (chunked, mean-pooled) ── cosine ──► semantic ranking
        └── skill coverage + experience fit
                        │
       Hybrid score = 0.5·SBERT(calibrated) + 0.4·skill coverage + 0.1·experience fit
                        │
      ranked jobs · matched / partial / missing skills · recommendations
```

* **Preprocessing:** lowercasing, URL/email removal, tokenisation, stop-word removal and lemmatisation with spaCy (for TF-IDF). Tech tokens like `c++`, `c#`, `.net` and `node.js` are kept.
* **Skill extraction:** `data/skills.json` holds 173 canonical skills in 14 categories (about 540 aliases), each with aliases (`"React": ["react", "reactjs", "react.js"]`). A spaCy `PhraseMatcher` maps every mention to its canonical name.
* **Required vs preferred:** lines under headings such as *Preferred / Nice to have / Bonus*, or lines containing those words, are treated as preferred.
* **Semantic matching:** long documents are split into chunks of about 120 words, embedded, then mean-pooled and L2-normalised. Cosine similarity is a dot product of the normalised vectors.
* **Skill gap:** exact canonical match first. A missing job skill counts as *partially covered* if one of the candidate's skills is semantically close to it (SBERT cosine ≥ 0.65, e.g. TensorFlow ≈ PyTorch). Skill coverage = 75 % required + 25 % preferred, with partial matches getting half credit.
* **Recommendations:** missing skills are aggregated over the top-K jobs. Priority = 2 × (jobs requiring the skill) + 1 × (jobs preferring it), with half weight if a related skill is already present.

## Evaluation

```powershell
python evaluate.py                                     # hand-labelled sample set
python evaluate.py --model sentence-transformers/all-mpnet-base-v2
python evaluate.py --kaggle-resumes data/external/UpdatedResumeDataSet.csv --per-category 20
```

* **Skill extraction:** micro and macro Precision / Recall / F1 against `data/eval/annotations.json`. The annotations are hand-labelled and include skills written in other words (e.g. "neural nets" → Deep Learning), so the scores are not inflated. The script also prints missed and extra skills per resume for error analysis.
* **Ranking:** P@1/3/5, Recall@K, nDCG@K and MRR for **TF-IDF vs SBERT vs Hybrid**.
  * Sample set: relevance is labelled by hand (`relevant_jobs`).
  * Kaggle set: a job is relevant when its category equals the resume's category.

Results are written to `results/eval_results.md` / `.json` and shown in the app's *Evaluation* tab.

> The bundled sample set is small (8 resumes, 30 jobs) and is meant to demonstrate the pipeline.
> For the final report, add more annotated resumes to `annotations.json` and/or run on a public dataset.

## Public datasets (download manually, put in `data/external/`)

* **Updated Resume Dataset** (Kaggle, ~960 resumes, 25 categories, columns `Category, Resume`). Its categories match `data/jobs.json`.
* **Resume Dataset** by snehaanbhawal (Kaggle, ~2400 resumes, columns `Category, Resume_str`).
* **LinkedIn Job Postings 2023–24** (Kaggle). Load it with `--jobs`; columns `title` and `description` are detected automatically.

You can also upload your own jobs CSV (`title`, `description`, optional `company`, `category`, `location`) in the app sidebar.

## Project structure

```
app.py               Streamlit UI
evaluate.py          experiments (P/R/F1, P@K, MRR, nDCG) + comparison tables
src/parser.py        text extraction, sections, contact, education, experience, JD required/preferred split
src/preprocess.py    cleaning, spaCy tokenisation / lemmatisation, sentence split, chunking
src/skills.py        taxonomy-based skill extractor (spaCy PhraseMatcher)
src/matcher.py       TfidfMatcher (baseline), SemanticMatcher (SBERT), explanations
src/gap.py           skill-gap analysis + recommendations
src/pipeline.py      end-to-end pipeline and hybrid scoring
src/evaluation.py    metric implementations
data/skills.json     skill taxonomy (edit to add skills)
data/jobs.json       30 sample job descriptions (fictional companies)
data/sample_resumes/ 8 sample resumes (fictional people)
data/eval/           hand-labelled ground truth
```

## Scope

In scope: resume analysis, job matching, skill-gap identification, recommendations and explainable results.
Out of scope: automatic job applications, training LLMs from scratch, LinkedIn scraping and making recruitment decisions.
The system is a decision-support tool, not a hiring decision maker.

## Limitations

* Skill extraction is dictionary-based. Skills that are not in `skills.json`, or are described only indirectly, can be missed. Extending the taxonomy (e.g. from ESCO / O*NET) improves recall.
* Scanned (image-only) PDFs need OCR, which is not included.
* Experience years are estimated from date ranges in the experience section.
* The SBERT score calibration bounds (0.15–0.70) were chosen for MiniLM. Re-check them if you change the model.
