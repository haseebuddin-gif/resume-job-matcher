import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Quality } from '../core/models';
import { Icon } from '../shared/icon';
import { ScoreRing } from '../shared/score-ring';

@Component({
  selector: 'app-quality-dialog',
  imports: [Icon, ScoreRing],
  template: `
    <div class="dialog" style="width: min(640px, 94vw)">
      <div class="dialog-head">
        <app-score-ring [value]="q.score / 100" [size]="56" />
        <div class="spacer">
          <h2>Resume quality: {{ q.grade }}</h2>
          <p>{{ passed }} of {{ q.checks.length }} checks passed · {{ q.stats.words }} words · {{ q.stats.bullets }} bullet points</p>
        </div>
        <button class="btn btn-ghost icon-btn" (click)="ref.close()" aria-label="Close"><app-icon name="x" /></button>
      </div>
      <div class="dialog-body">
        @if (failed.length) {
          <div class="section-label">Improve</div>
          <ul class="checks">
            @for (c of failed; track c.id) {
              <li class="fail"><app-icon name="x-circle" [size]="18" />
                <div><strong>{{ c.label }}</strong><p>{{ c.tip }}</p></div><span class="pts">+{{ c.weight }}</span></li>
            }
          </ul>
        }
        <div class="section-label" style="margin-top: 16px">Passed</div>
        <ul class="checks">
          @for (c of passedChecks; track c.id) {
            <li class="ok"><app-icon name="check-circle" [size]="18" /><div><strong>{{ c.label }}</strong></div></li>
          }
        </ul>
        <p class="hint" style="margin-top: 14px">Rule-based checks of structure and content, similar to what applicant tracking systems look for. Points show each check's weight.</p>
      </div>
    </div>
  `,
  styles: `
    .checks { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    li { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); }
    li div { flex: 1; } li p { color: var(--text-2); font-size: 13px; margin-top: 2px; }
    li.fail app-icon { color: var(--bad); } li.ok app-icon { color: var(--good); }
    li.ok { padding: 8px 12px; }
    .pts { font-size: 12px; font-weight: 600; color: var(--muted); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualityDialog {
  protected ref = inject(DialogRef);
  protected q = inject<Quality>(DIALOG_DATA);
  protected failed = this.q.checks.filter(c => !c.passed).sort((a, b) => b.weight - a.weight);
  protected passedChecks = this.q.checks.filter(c => c.passed);
  protected passed = this.passedChecks.length;
}
