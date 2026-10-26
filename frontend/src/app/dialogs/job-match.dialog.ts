import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ApiService, errorMessage } from '../core/api.service';
import { Explanation, Job, JobMatch, Weights } from '../core/models';
import { EvidenceList } from '../shared/evidence-list';
import { GapView } from '../shared/gap-view';
import { Icon } from '../shared/icon';
import { ScoreBreakdown } from '../shared/score-breakdown';
import { ScoreRing, scoreBand } from '../shared/score-ring';

export interface JobMatchData {
  match: JobMatch;
  resumeText: string;
  model: string;
  weights: Weights | null;
  candidateName: string;
  candidateYears: number;
}

type Tab = 'overview' | 'evidence' | 'description';

@Component({
  selector: 'app-job-match-dialog',
  imports: [Icon, ScoreRing, ScoreBreakdown, GapView, EvidenceList],
  template: `
    <div class="dialog" style="width: min(880px, 95vw)">
      <div class="dialog-head">
        <app-score-ring [value]="m.scores.hybrid" [size]="56" />
        <div class="spacer">
          <div class="row wrap" style="gap: 6px"><h2>{{ m.title }}</h2><span class="badge" [class]="band.cls">{{ band.label }}</span></div>
          <p class="row wrap meta">
            @if (m.company) { <span><app-icon name="building" [size]="13" />{{ m.company }}</span> }
            @if (m.location) { <span><app-icon name="pin" [size]="13" />{{ m.location }}</span> }
            @if (m.category) { <span><app-icon name="briefcase" [size]="13" />{{ m.category }}</span> }
          </p>
        </div>
        <button class="btn btn-ghost icon-btn" (click)="ref.close()" aria-label="Close"><app-icon name="x" /></button>
      </div>

      <div class="tabs dialog-tabs">
        <button [class.active]="tab() === 'overview'" (click)="tab.set('overview')">Score & skill gap</button>
        <button [class.active]="tab() === 'evidence'" (click)="tab.set('evidence')">Why this match</button>
        <button [class.active]="tab() === 'description'" (click)="openDescription()">Job description</button>
      </div>

      <div class="dialog-body">
        @switch (tab()) {
          @case ('overview') {
            <div class="grid grid-2" style="gap: 28px">
              <section>
                <h3 class="h">Score breakdown</h3>
                <app-score-breakdown [match]="m" [weights]="data.weights" [candidateYears]="data.candidateYears" />
              </section>
              <section>
                <h3 class="h">Skill gap</h3>
                <app-gap-view [gap]="m.gap" />
              </section>
            </div>
          }
          @case ('evidence') {
            <p class="text-2 small" style="margin-bottom: 12px">
              Each job requirement is paired with the most similar sentence in the resume (Sentence-BERT cosine similarity).
            </p>
            @if (explanation(); as ex) {
              <app-evidence-list [evidence]="ex.evidence" />
              @if (ex.keywords.length) {
                <h3 class="h" style="margin-top: 20px">Shared keywords (TF-IDF)</h3>
                <div class="chips">@for (k of ex.keywords; track k) { <span class="chip accent">{{ k }}</span> }</div>
              }
            } @else if (explainError()) {
              <div class="callout warn"><app-icon name="alert" />{{ explainError() }}</div>
            } @else {
              @for (i of [1, 2, 3]; track i) { <div class="skeleton" style="height: 64px; margin-bottom: 10px"></div> }
            }
          }
          @case ('description') {
            @if (job(); as j) {
              <pre class="desc">{{ j.description }}</pre>
            } @else {
              <div class="skeleton" style="height: 240px"></div>
            }
          }
        }
      </div>

      <div class="dialog-foot">
        <button class="btn" (click)="downloadReport()"><app-icon name="download" [size]="15" />Download gap report</button>
        <span class="spacer"></span>
        <button class="btn btn-primary" (click)="ref.close()">Done</button>
      </div>
    </div>
  `,
  styles: `
    .meta { color: var(--text-2); font-size: 13px; gap: 14px; margin-top: 4px; }
    .meta span { display: inline-flex; align-items: center; gap: 5px; }
    .dialog-tabs { padding: 0 20px; margin: 0; }
    .h { margin-bottom: 14px; }
    .desc { white-space: pre-wrap; font: inherit; margin: 0; color: var(--text-2); line-height: 1.65; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobMatchDialog {
  protected ref = inject(DialogRef);
  protected data = inject<JobMatchData>(DIALOG_DATA);
  private api = inject(ApiService);

  protected m = this.data.match;
  protected band = scoreBand(this.m.scores.hybrid);
  protected tab = signal<Tab>('overview');
  protected explanation = signal<Explanation | null>(null);
  protected explainError = signal('');
  protected job = signal<Job | null>(null);

  constructor() {
    // fetched up-front so the "Why this match" tab opens instantly
    this.api.explain(this.data.resumeText, this.m.job_id, this.data.model).subscribe({
      next: e => this.explanation.set(e),
      error: e => this.explainError.set(errorMessage(e)),
    });
  }

  protected openDescription() {
    this.tab.set('description');
    if (!this.job()) {
      this.api.job(this.m.job_id).subscribe(j => this.job.set(j));
    }
  }

  protected downloadReport() {
    const report = {
      candidate: this.data.candidateName,
      job: { id: this.m.job_id, title: this.m.title, company: this.m.company },
      scores: this.m.scores,
      skill_gap: this.m.gap,
      evidence: this.explanation()?.evidence ?? [],
      generated: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `skill-gap-${this.m.job_id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
}
