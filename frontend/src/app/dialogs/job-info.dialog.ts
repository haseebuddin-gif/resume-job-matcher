import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Job } from '../core/models';
import { Icon } from '../shared/icon';

@Component({
  selector: 'app-job-info-dialog',
  imports: [Icon],
  template: `
    <div class="dialog" style="width: min(780px, 95vw)">
      <div class="dialog-head">
        <div class="spacer">
          <div class="row wrap" style="gap: 6px"><h2>{{ job.title }}</h2>
            @if (job.source === 'custom') { <span class="badge accent">Added by you</span> }</div>
          <p class="row wrap meta">
            @if (job.company) { <span><app-icon name="building" [size]="13" />{{ job.company }}</span> }
            @if (job.location) { <span><app-icon name="pin" [size]="13" />{{ job.location }}</span> }
            @if (job.category) { <span><app-icon name="briefcase" [size]="13" />{{ job.category }}</span> }
          </p>
        </div>
        <button class="btn btn-ghost icon-btn" (click)="ref.close()" aria-label="Close"><app-icon name="x" /></button>
      </div>
      <div class="dialog-body">
        <div class="grid grid-2 facts">
          <div><div class="section-label">Required skills (extracted)</div>
            <div class="chips">@for (s of job.required_skills; track s) { <span class="chip accent">{{ s }}</span> } @empty { <span class="muted small">None recognised</span> }</div></div>
          <div><div class="section-label">Preferred skills (extracted)</div>
            <div class="chips">@for (s of job.preferred_skills; track s) { <span class="chip outline">{{ s }}</span> } @empty { <span class="muted small">None</span> }</div></div>
          <div><div class="section-label">Minimum experience</div><p>{{ job.min_years ? job.min_years + '+ years' : 'Not stated' }}</p></div>
          <div><div class="section-label">Degree</div><p>{{ job.required_degree || 'Not stated' }}</p></div>
        </div>
        <div class="section-label" style="margin-top: 20px">Description</div>
        <pre class="desc">{{ job.description }}</pre>
      </div>
      <div class="dialog-foot">
        @if (job.source === 'custom') {
          <button class="btn btn-danger" (click)="ref.close('delete')"><app-icon name="trash" [size]="15" />Delete job</button>
          <span class="spacer"></span>
        }
        <button class="btn btn-primary" (click)="ref.close()">Close</button>
      </div>
    </div>
  `,
  styles: `
    .meta { color: var(--text-2); font-size: 13px; gap: 14px; margin-top: 4px; }
    .meta span { display: inline-flex; align-items: center; gap: 5px; }
    .facts { gap: 18px; }
    .desc { white-space: pre-wrap; font: inherit; margin: 0; color: var(--text-2); line-height: 1.65; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobInfoDialog {
  protected ref = inject<DialogRef<'delete'>>(DialogRef);
  protected job = inject<Job>(DIALOG_DATA);
}
