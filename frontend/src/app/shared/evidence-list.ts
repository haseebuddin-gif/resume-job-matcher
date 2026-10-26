import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { Evidence } from '../core/models';

/** "Why this match": job requirement sentences paired with the closest resume sentence. */
@Component({
  selector: 'app-evidence-list',
  imports: [DecimalPipe],
  template: `
    <ol class="ev">
      @for (e of evidence(); track $index) {
        <li>
          <div class="pair">
            <div><span class="tag">Job asks</span><p>{{ e.job_requirement }}</p></div>
            <div><span class="tag res">Resume shows</span><p>{{ e.resume_evidence }}</p></div>
          </div>
          <span class="sim tnum" title="Sentence-BERT cosine similarity">{{ e.similarity | number: '1.2-2' }}</span>
        </li>
      } @empty {
        <li class="muted small">No sentence-level evidence found.</li>
      }
    </ol>
  `,
  styles: `
    .ev { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
    li { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-2); }
    .pair { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .tag { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
    .tag.res { color: var(--accent-text); }
    p { font-size: 13px; margin-top: 3px; }
    .sim { font-weight: 650; font-size: 13px; padding: 2px 8px; border-radius: 6px; background: var(--surface); border: 1px solid var(--border); }
    @media (max-width: 640px) { .pair { grid-template-columns: 1fr; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EvidenceList {
  readonly evidence = input.required<Evidence[]>();
}
