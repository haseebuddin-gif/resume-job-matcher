# SkillMatch: AI-Based Resume–Job Matching and Skill Gap Analysis Using NLP

Upload a resume and get a **ranked list of suitable jobs** with a **match score, matched skills, missing skills and a prioritised learning roadmap**.
The project compares a traditional **TF-IDF + Cosine Similarity** baseline with **Sentence Transformer (SBERT)** semantic matching and a **hybrid** score.

Everything runs locally with open-source models. No paid AI API is used.

| Layer | Technology |
|---|---|
| NLP / ML | Python, spaCy, scikit-learn, Sentence Transformers (Hugging Face), PyTorch, pandas, NumPy |
| API | FastAPI (REST, OpenAPI docs at `/docs`) |
| Web app | Angular 22 (standalone components, signals, CDK dialogs) |
| Demo UI | Streamlit (`app.py`, as listed in the proposal) |

## Features

* **Resume parsing** for PDF, DOCX and TXT: sections, contact details, education, estimated years of experience.
* **Skill extraction**: 173 skills (about 540 aliases) in 14 categories, matched with spaCy PhraseMatcher (longest match wins).
* **Job profiles**: required vs preferred skills, minimum years and degree are extracted from each job description.
* **Three ranking methods**: TF-IDF baseline, SBERT semantic similarity, and a hybrid of semantic + skill coverage + experience fit + education fit, with adjustable weights.
* **Two Transformer models**: all-MiniLM-L6-v2 (fast) and all-mpnet-base-v2 (more accurate).
* **Explainability**: score breakdown, matched / related / missing skills, sentence-level evidence ("job asks" ↔ "resume shows"), and shared TF-IDF keywords.
* **Skill-gap report and learning roadmap**: missing skills across the top jobs, prioritised into *Focus now / Next / Later* with advice.
* **Resume quality (ATS) check**: 12 weighted checks with improvement tips.
* **Match any job description** pasted by the user, without adding it to the library.
* **Job library**: browse and search jobs, or add and delete your own.
* **Evaluation dashboard**: P/R/F1, MRR, P@K, Recall@K and nDCG@K, an ablation study, a model comparison and per-resume error analysis.
* **Report export** to PDF (print layout), a JSON gap report per job, local analysis history, dark mode, and a responsive layout.

## Quick start (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File run.ps1
```

On the first run this creates the Python environment, installs dependencies, builds the Angular app and opens **http://localhost:8000**.
The Sentence Transformer model (~90 MB) is downloaded once from Hugging Face; after that the app works offline.

### Manual setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m spacy download en_core_web_sm

cd frontend; npm install; npx ng build; cd ..
uvicorn api.main:app --port 8000          # app + API at http://localhost:8000
```

### Development mode (hot reload)

```powershell
uvicorn api.main:app --port 8000 --reload  # terminal 1
cd frontend; npx ng serve                  # terminal 2 -> http://localhost:4200 (proxies /api to :8000)
```

### Streamlit demo

```powershell
streamlit run app.py
```

## How it works

```
Resume (PDF/DOCX/TXT)                        Job descriptions
        │                                          │
  text extraction · section split                  split into required / preferred
  contact · education · experience years           min. years · degree
        │                                          │
  skill extraction (spaCy PhraseMatcher + taxonomy) ┤
        │                                          │
        ├── TF-IDF (lemmatised 1–2 grams) ── cosine ──► baseline ranking
        ├── SBERT embeddings (chunked, mean-pooled) ── cosine ──► semantic ranking
        └── skill coverage · experience fit · education fit
                        │
   match = 0.45·semantic + 0.35·skills + 0.10·experience + 0.10·education   (weights adjustable)
                        │
   ranked jobs · evidence · matched / related / missing skills · roadmap · quality report
```

* **Preprocessing:** lowercasing, URL/e-mail removal, tokenisation, stop-word removal and spaCy lemmatisation. Tech terms (`c++`, `c#`, `.net`) and taxonomy words are not lemmatised, so "data" stays "data" and is not turned into "datum".
* **Semantic matching:** documents are split into ~120-word chunks, embedded, mean-pooled and L2-normalised. The raw cosine is calibrated to 0–1 as `clip((cos − 0.15) / 0.55, 0, 1)`.
* **Skill gap:** exact canonical matches first. A missing skill counts as *related / partially covered* when a candidate skill is semantically close (SBERT cosine ≥ 0.65, e.g. TensorFlow ≈ PyTorch) and gets half credit. Skill coverage = 75% required + 25% preferred.
* **Recommendations:** priority = 2 × (top jobs requiring the skill) + 1 × (top jobs preferring it), halved for related skills.
* **Semantic skill inference** (optional, off by default): multi-word noun phrases are matched to skill aliases with embeddings. See the ablation results below.

## Evaluation

```powershell
python evaluate.py                       # hand-labelled sample set -> results/eval_results.md
python evaluate.py --compare-models      # also rank with all-mpnet-base-v2
python evaluate.py --kaggle-resumes data/external/UpdatedResumeDataSet.csv --per-category 20
```

Current results on the bundled hand-labelled set (8 resumes, 30 jobs):

| Skill extraction (micro) | Precision | Recall | F1 |
|---|---|---|---|
| Dictionary (PhraseMatcher) | 0.990 | 0.933 | **0.961** |
| Dictionary + semantic inference | 0.980 | 0.933 | 0.956 |

| Ranking (all-MiniLM-L6-v2) | MRR | P@3 | Recall@3 | nDCG@5 |
|---|---|---|---|---|
| TF-IDF + cosine (baseline) | 1.000 | 0.625 | 0.938 | 0.985 |
| SBERT + cosine | 1.000 | 0.625 | 0.938 | 0.981 |
| **Hybrid** | 1.000 | **0.667** | **1.000** | **0.990** |

The hybrid method performs best. On this small, clean sample, SBERT alone does no better than TF-IDF because the resumes and jobs share most keywords. With all-mpnet-base-v2, SBERT alone is slightly lower (MRR 0.938) while the hybrid reaches nDCG@5 = 1.000. Semantic inference did not improve recall on this set, so it is off by default. These are honest results on a small demonstration set. For the final report, run the Kaggle evaluation (relevance = resume category equals job category), where vocabulary differences are larger.

The same results are shown in the app's **Evaluation** page, which can also re-run the experiment.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/config` | models, methods, default weights, sample resumes |
| POST | `/api/analyze` | multipart: `file` or `text` or `sample_name`, plus `method`, `model`, `top_k`, `w_*`, `infer_skills` |
| POST | `/api/explain` | sentence evidence + shared keywords for one job |
| POST | `/api/match-custom` | score a resume against any pasted job description |
| POST | `/api/extract-text` | text from an uploaded file |
| GET/POST/DELETE | `/api/jobs`, `/api/jobs/{id}` | job library (only user-added jobs can be deleted) |
| GET/POST | `/api/evaluation`, `/api/evaluation/run` | stored results / run the experiment |

Interactive documentation: http://localhost:8000/docs

## Tests

```powershell
python tests/test_app.py    # parsing, skill extraction, Streamlit app end-to-end
python tests/test_api.py    # REST API end-to-end (analyze, upload, explain, custom JD, jobs CRUD)
```

## Project structure

```
api/main.py            FastAPI app (also serves the built Angular app)
frontend/              Angular app: pages/ (analyze, results, jd-match, jobs, evaluation, about),
                       dialogs/ (job match, quality, add job, confirm, preview), shared/ components
src/parser.py          text extraction, sections, contact, education, experience, JD requirement split
src/preprocess.py      cleaning, spaCy tokenisation / lemmatisation, sentence split, chunking
src/skills.py          taxonomy skill extractor + optional semantic inference
src/matcher.py         TfidfMatcher (baseline), SemanticMatcher (SBERT), explanations
src/gap.py             skill-gap analysis + recommendations / roadmap
src/quality.py         resume quality (ATS) checks
src/pipeline.py        end-to-end pipeline, hybrid scoring, JSON serialisation
src/evaluation.py      metric implementations
evaluate.py            experiments and comparison tables
app.py                 Streamlit demo UI
data/skills.json       skill taxonomy (edit to add skills)
data/jobs.json         30 sample job descriptions (fictional companies)
data/sample_resumes/   8 sample resumes (fictional people)
data/eval/             hand-labelled ground truth
```

## Public datasets (download manually into `data/external/`)

* **Updated Resume Dataset** (Kaggle, ~960 resumes, 25 categories, columns `Category, Resume`). Its categories match `data/jobs.json`.
* **Resume Dataset** by snehaanbhawal (Kaggle, ~2400 resumes, columns `Category, Resume_str`).
* **LinkedIn Job Postings 2023–24** (Kaggle). Use it with `--jobs`; `title` and `description` columns are detected automatically.

## Scope and limitations

In scope: resume analysis, job matching, skill-gap identification, recommendations and explainable results.
Out of scope: automatic job applications, training LLMs from scratch, LinkedIn scraping and recruitment decision-making. The scores support a person's judgement; they do not replace it.

* Dictionary-based extraction misses skills that are absent from `skills.json` or described only indirectly.
* Scanned (image-only) PDFs need OCR, which is not included.
* Experience is estimated from date ranges in the experience section.
* The semantic calibration bounds (0.15–0.70) were chosen for MiniLM. Re-check them for other models.
