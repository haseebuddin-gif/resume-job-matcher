import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Icon } from '../../shared/icon';

const STEPS = [
  { title: 'Text extraction', body: 'pdfplumber and python-docx read PDF, DOCX and TXT files; whitespace and bullet characters are normalised.' },
  { title: 'Section & field parsing', body: 'Headings split the resume into summary, skills, experience, education and projects. Regular expressions extract contact details, degrees and date ranges; overlapping date ranges are merged to estimate years of experience.' },
  { title: 'Preprocessing', body: 'Lower-casing, URL/e-mail removal, tokenisation, stop-word removal and lemmatisation with spaCy. Technical tokens such as C++, C# and .NET are preserved.' },
  { title: 'Skill extraction', body: 'A taxonomy of 173 skills (about 540 aliases) in 14 categories is matched with spaCy PhraseMatcher; the longest overlapping match wins, so “SQL Server” is not also counted as “SQL”. Job descriptions are split into required and preferred parts.' },
  { title: 'Baseline: TF-IDF', body: 'Unigram and bigram TF-IDF vectors with sublinear term frequency; resumes and jobs are compared with cosine similarity.' },
  { title: 'Proposed: Sentence-BERT', body: 'Documents are split into ~120-word chunks, embedded with a pretrained Sentence Transformer (all-MiniLM-L6-v2 or all-mpnet-base-v2), mean-pooled and L2-normalised. Cosine similarity measures semantic compatibility.' },
  { title: 'Hybrid ranking', body: 'The calibrated semantic score is combined with skill coverage, experience fit and education fit using adjustable weights.' },
  { title: 'Skill gap & recommendations', body: 'Missing required and preferred skills are listed per job. A missing skill counts as partially covered when a candidate skill is semantically close (cosine ≥ 0.65). Gaps across the top jobs are aggregated into a prioritised learning roadmap.' },
];

@Component({
  selector: 'app-about-page',
  imports: [Icon],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Methodology</h1>
          <p>How the system turns a resume into ranked jobs and a skill-gap report. Everything runs locally with open-source models; no paid AI API is used.</p>
        </div>
      </header>

      <div class="grid grid-main">
        <section class="card">
          <div class="card-head"><h2>Pipeline</h2></div>
          <ol class="steps card-body">
            @for (s of steps; track s.title; let i = $index) {
              <li><span class="num">{{ i + 1 }}</span><div><h3>{{ s.title }}</h3><p>{{ s.body }}</p></div></li>
            }
          </ol>
        </section>

        <div class="stack" style="gap: 16px">
          <section class="card">
            <div class="card-head"><h2>Scoring</h2></div>
            <div class="card-body stack small">
              <div class="formula">match = w<sub>s</sub>·semantic + w<sub>k</sub>·skills + w<sub>e</sub>·experience + w<sub>d</sub>·education</div>
              <p class="text-2">Default weights 0.45 / 0.35 / 0.10 / 0.10, normalised to sum to 1.</p>
              <div class="formula">semantic = clip((cos − 0.15) / (0.70 − 0.15), 0, 1)</div>
              <div class="formula">skills = 0.75·required coverage + 0.25·preferred coverage</div>
              <p class="text-2">Partially covered skills earn half credit. Experience fit = min(1, candidate years / required years).</p>
            </div>
          </section>
          <section class="card">
            <div class="card-head"><h2>Evaluation metrics</h2></div>
            <dl class="card-body kv small">
              <dt>Extraction</dt><dd>Precision, Recall, F1 (micro and macro)</dd>
              <dt>Ranking</dt><dd>MRR, Precision@K, Recall@K, nDCG@K</dd>
              <dt>Comparison</dt><dd>TF-IDF vs SBERT vs Hybrid, Spearman rank correlation</dd>
            </dl>
          </section>
          <section class="card">
            <div class="card-head"><h2>Technology</h2></div>
            <div class="card-body chips">
              @for (t of tech; track t) { <span class="chip">{{ t }}</span> }
            </div>
          </section>
          <section class="card">
            <div class="card-head"><h2>Scope</h2></div>
            <div class="card-body small text-2 stack" style="gap: 8px">
              <p>In scope: resume analysis, job matching, skill-gap identification, recommendations and explainable results.</p>
              <p>Out of scope: automatic job applications, training language models from scratch, LinkedIn scraping, and making hiring decisions. Scores support a person's judgement; they do not replace it.</p>
            </div>
          </section>
          <div class="callout warn small"><app-icon name="alert" [size]="15" />
            <div>Limitations: dictionary-based extraction misses skills absent from the taxonomy; scanned PDFs need OCR; experience is estimated from dates.</div></div>
        </div>
      </div>
    </div>
  `,
  styles: `
    .steps { list-style: none; margin: 0; display: flex; flex-direction: column; gap: 0; }
    .steps li { display: flex; gap: 14px; position: relative; padding-bottom: 18px; }
    .steps li:not(:last-child)::before { content: ''; position: absolute; left: 13px; top: 30px; bottom: 2px; width: 1px; background: var(--border); }
    .num { width: 27px; height: 27px; flex: none; border-radius: 50%; display: grid; place-items: center; font-size: 12.5px; font-weight: 650;
           background: var(--accent-weak); color: var(--accent-text); }
    .steps h3 { margin: 3px 0 4px; }
    .steps p { color: var(--text-2); font-size: 13.5px; }
    .formula { font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace; font-size: 12.5px; padding: 10px 12px; border-radius: 8px;
               background: var(--surface-2); border: 1px solid var(--border); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AboutPage {
  protected readonly steps = STEPS;
  protected readonly tech = ['Python', 'spaCy', 'scikit-learn', 'Sentence Transformers', 'Hugging Face Transformers', 'PyTorch',
    'pandas', 'NumPy', 'FastAPI', 'Angular', 'Streamlit (demo)'];
}
