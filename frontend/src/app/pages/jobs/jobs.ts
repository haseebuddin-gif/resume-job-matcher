import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { filter, switchMap } from 'rxjs';
import { ApiService, errorMessage } from '../../core/api.service';
import { Job, JobList } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { AddJobDialog } from '../../dialogs/add-job.dialog';
import { Dialogs } from '../../dialogs/dialogs';
import { JobInfoDialog } from '../../dialogs/job-info.dialog';
import { Icon } from '../../shared/icon';

@Component({
  selector: 'app-jobs-page',
  imports: [FormsModule, Icon],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Job library</h1>
          <p>The job descriptions every resume is matched against. Required and preferred skills are extracted automatically.</p>
        </div>
        <button class="btn btn-primary" (click)="addJob()"><app-icon name="plus" [size]="15" />Add job</button>
      </header>

      <div class="toolbar card">
        <div class="search">
          <app-icon name="search" [size]="15" />
          <input class="input" placeholder="Search title, company or description" [ngModel]="query()" (ngModelChange)="query.set($event)" aria-label="Search jobs" />
        </div>
        <select class="select" style="width: 220px" [ngModel]="category()" (ngModelChange)="category.set($event)" aria-label="Filter by category">
          <option value="">All categories</option>
          @for (c of data()?.categories ?? []; track c) { <option [value]="c">{{ c }}</option> }
        </select>
        <span class="muted small count">{{ filtered().length }} of {{ data()?.total ?? 0 }} jobs</span>
      </div>

      @if (loading()) {
        <div class="job-grid">@for (i of [1,2,3,4,5,6]; track i) { <div class="skeleton" style="height: 150px"></div> }</div>
      } @else {
        <div class="job-grid">
          @for (j of filtered(); track j.job_id) {
            <article class="card job" tabindex="0" (click)="open(j)" (keydown.enter)="open(j)">
              <div class="row" style="align-items: flex-start">
                <div class="spacer"><h3>{{ j.title }}</h3><p class="muted small">{{ j.company }}@if (j.location) { · {{ j.location }} }</p></div>
                @if (j.source === 'custom') { <span class="badge accent">Custom</span> }
              </div>
              <div class="chips">
                @for (s of j.required_skills.slice(0, 5); track s) { <span class="chip">{{ s }}</span> }
                @if (j.required_skills.length > 5) { <span class="chip outline">+{{ j.required_skills.length - 5 }}</span> }
              </div>
              <div class="job-foot small muted">
                <span>{{ j.category || 'Uncategorised' }}</span>
                <span>{{ j.min_years ? j.min_years + '+ yrs' : 'Any experience' }}</span>
              </div>
            </article>
          } @empty {
            <div class="card empty" style="grid-column: 1 / -1"><div class="icon-wrap"><app-icon name="search" [size]="22" /></div>
              <h2>No jobs found</h2><p>Try a different search or category.</p></div>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .toolbar { display: flex; gap: 10px; align-items: center; padding: 10px; margin-bottom: 18px; flex-wrap: wrap; }
    .search { position: relative; flex: 1; min-width: 220px; }
    .search app-icon { position: absolute; left: 11px; top: 11px; color: var(--muted); }
    .search .input { padding-left: 33px; }
    .count { margin-left: auto; padding-right: 6px; }
    .job-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
    .job { padding: 16px; display: flex; flex-direction: column; gap: 12px; cursor: pointer; transition: border-color .12s, box-shadow .12s; }
    .job:hover { border-color: var(--border-strong); box-shadow: var(--shadow-md); }
    .job h3 { font-size: 14.5px; }
    .job-foot { display: flex; justify-content: space-between; margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobsPage {
  private api = inject(ApiService);
  private dialogs = inject(Dialogs);
  private toast = inject(ToastService);

  protected data = signal<JobList | null>(null);
  protected loading = signal(true);
  protected query = signal('');
  protected category = signal('');

  protected filtered = computed(() => {
    const q = this.query().trim().toLowerCase();
    const cat = this.category();
    return (this.data()?.jobs ?? []).filter(j =>
      (!cat || j.category === cat) &&
      (!q || `${j.title} ${j.company} ${j.description}`.toLowerCase().includes(q)));
  });

  constructor() { this.load(); }

  private load() {
    this.api.jobs().subscribe({
      next: d => { this.data.set(d); this.loading.set(false); },
      error: e => { this.loading.set(false); this.toast.error('Could not load jobs', errorMessage(e)); },
    });
  }

  protected open(job: Job) {
    this.dialogs.open<'delete', Job, JobInfoDialog>(JobInfoDialog, job).pipe(
      filter(action => action === 'delete'),
      switchMap(() => this.dialogs.confirm({
        title: 'Delete this job?', message: `"${job.title}" will be removed from the library. This cannot be undone.`,
        confirmLabel: 'Delete', danger: true,
      })),
      filter(Boolean),
      switchMap(() => this.api.deleteJob(job.job_id)),
    ).subscribe({
      next: () => { this.toast.success('Job deleted', job.title); this.load(); },
      error: e => this.toast.error('Could not delete job', errorMessage(e)),
    });
  }

  protected addJob() {
    this.dialogs.open<Job, { categories: string[] }, AddJobDialog>(AddJobDialog, { categories: this.data()?.categories ?? [] })
      .subscribe(job => {
        if (!job) return;
        this.toast.success('Job added', `${job.title} · ${job.required_skills.length} required skills detected`);
        this.load();
      });
  }
}
