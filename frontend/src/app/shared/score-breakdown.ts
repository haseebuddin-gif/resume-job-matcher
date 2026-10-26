import { DecimalPipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { JobMatch, Weights } from '../core/models';

/** Bars for each component of the hybrid score plus the raw cosine similarities. */
@Component({
  selector: 'app-score-breakdown',
  imports: [PercentPipe, DecimalPipe],
  template: `
    <div class="rows">
      @for (r of rows(); track r.label) {
        <div class="r">
          <div class="top">
            <span>{{ r.label }}</span>
            @if (weights(); as w) { <span class="w">weight {{ r.weight(w) | percent }}</span> }
            <span class="spacer"></span>
            <span class="v tnum">{{ r.value === null ? 'n/a' : (r.value | percent) }}</span>
          </div>
          <div class="meter" [class]="r.value === null ? '' : r.value >= .65 ? 'good' : r.value >= .4 ? '' : 'warn'">
            <div [style.width.%]="(r.value ?? 0) * 100"></div>
          </div>
          <span class="note">{{ r.note }}</span>
        </div>
      }
    </div>
    <div class="raw">
      <div><span class="muted">SBERT cosine</span><strong class="tnum">{{ match().scores.sbert | number: '1.3-3' }}</strong></div>
      <div><span class="muted">TF-IDF cosine</span><strong class="tnum">{{ match().scores.tfidf | number: '1.3-3' }}</strong></div>
      <div><span class="muted">Rank (hybrid / SBERT / TF-IDF)</span>
        <strong class="tnum">{{ match().ranks.hybrid }} / {{ match().ranks.sbert }} / {{ match().ranks.tfidf }}</strong></div>
    </div>
  `,
  styles: `
    .rows { display: flex; flex-direction: column; gap: 14px; }
    .top { display: flex; gap: 8px; align-items: baseline; font-size: 13.5px; margin-bottom: 6px; }
    .w { font-size: 11.5px; color: var(--muted); }
    .v { font-weight: 600; }
    .note { display: block; font-size: 12px; color: var(--muted); margin-top: 4px; }
    .raw { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }
    .raw div { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
    .raw strong { font-size: 14px; }
    @media (max-width: 600px) { .raw { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScoreBreakdown {
  readonly match = input.required<JobMatch>();
  readonly weights = input<Weights | null>(null);
  readonly candidateYears = input<number | null>(null);

  protected rows = computed(() => {
    const m = this.match();
    const years = this.candidateYears();
    const g = m.gap;
    const req = m.required_skills.length, pref = m.preferred_skills.length;
    const share = (k: keyof Weights) => (w: Weights) => {
      const total = w.semantic + w.skills + w.experience + w.education;
      return total ? w[k] / total : 0;
    };
    return [
      { label: 'Semantic similarity', value: m.scores.semantic, weight: share('semantic'),
        note: 'Sentence-BERT similarity between the whole resume and job, rescaled to 0–100%.' },
      { label: 'Skill coverage', value: m.scores.skill, weight: share('skills'),
        note: req + pref === 0 ? 'No recognised skills in this job description.'
          : `${g.matched_required.length}/${req} required and ${g.matched_preferred.length}/${pref} preferred skills; related skills count half.` },
      { label: 'Experience fit', value: m.scores.experience, weight: share('experience'),
        note: m.min_years ? `Job asks for ${m.min_years}+ years${years !== null ? `; resume shows about ${years}` : ''}.` : 'No minimum experience stated.' },
      { label: 'Education fit', value: m.scores.education, weight: share('education'),
        note: m.required_degree ? `Job mentions a ${m.required_degree} degree.` : 'No degree requirement stated.' },
    ];
  });
}
