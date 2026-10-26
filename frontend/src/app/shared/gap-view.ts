import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { Gap } from '../core/models';
import { Icon } from './icon';

@Component({
  selector: 'app-gap-view',
  imports: [Icon],
  template: `
    <div class="groups">
      <div>
        <div class="section-label">Matched skills · {{ gap().matched_required.length + gap().matched_preferred.length }}</div>
        <div class="chips">
          @for (s of gap().matched_required; track s) { <span class="chip good"><app-icon name="check" [size]="12" [stroke]="2.4" />{{ s }}</span> }
          @for (s of gap().matched_preferred; track s) { <span class="chip good" title="Preferred skill"><app-icon name="check" [size]="12" [stroke]="2.4" />{{ s }}<em>pref.</em></span> }
          @if (!gap().matched_required.length && !gap().matched_preferred.length) { <span class="muted small">None</span> }
        </div>
      </div>
      @if (gap().partial.length) {
        <div>
          <div class="section-label">Related skills · partially covered</div>
          <div class="chips">
            @for (p of gap().partial; track p.job_skill) {
              <span class="chip warn" [title]="'Similarity ' + p.similarity">{{ p.job_skill }}<span class="via">≈ {{ p.candidate_skill }}</span></span>
            }
          </div>
        </div>
      }
      <div>
        <div class="section-label">Missing required · {{ gap().missing_required.length }}</div>
        <div class="chips">
          @for (s of gap().missing_required; track s) { <span class="chip bad">{{ s }}</span> }
          @empty { <span class="muted small">None. All required skills are covered.</span> }
        </div>
      </div>
      <div>
        <div class="section-label">Missing nice-to-have · {{ gap().missing_preferred.length }}</div>
        <div class="chips">
          @for (s of gap().missing_preferred; track s) { <span class="chip outline">{{ s }}</span> }
          @empty { <span class="muted small">None</span> }
        </div>
      </div>
    </div>
  `,
  styles: `
    .groups { display: flex; flex-direction: column; gap: 16px; }
    em { font-style: normal; font-size: 11px; opacity: .75; margin-left: 2px; }
    .via { opacity: .8; margin-left: 4px; font-weight: 450; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GapView {
  readonly gap = input.required<Gap>();
}
