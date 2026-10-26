import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ApiService, errorMessage } from '../../core/api.service';
import { CustomMatchResult } from '../../core/models';
import { StateService } from '../../core/state.service';
import { ToastService } from '../../core/toast.service';
import { EvidenceList } from '../../shared/evidence-list';
import { GapView } from '../../shared/gap-view';
import { Icon } from '../../shared/icon';
import { ScoreBreakdown } from '../../shared/score-breakdown';
import { ScoreRing, scoreBand } from '../../shared/score-ring';

@Component({
  selector: 'app-jd-match-page',
  imports: [FormsModule, Icon, ScoreRing, ScoreBreakdown, GapView, EvidenceList, DecimalPipe],
  template: `
    <div class="page">
      <header class="page-head">
        <div>
          <h1>Match a job description</h1>
          <p>Paste any job posting to see how well a resume fits it, without adding the job to the library.</p>
        </div>
      </header>

      <div class="grid grid-2">
        <section class="card">
          <div class="card-head">
            <h2 class="spacer">Resume</h2>
            @if (state.result(); as r) {
              <button class="btn btn-sm" (click)="useCurrent()">Use {{ r.profile.name || 'current analysis' }}</button>
            }
            <label class="btn btn-sm">
              <app-icon name="upload" [size]="14" />Upload
              <input type="file" accept=".pdf,.docx,.txt" class="sr-only" (change)="upload($event)" />
            </label>
          </div>
          <div class="card-body">
            <textarea class="textarea" rows="16" placeholder="Paste resume text, upload a file, or reuse the current analysis"
                      [ngModel]="resume()" (ngModelChange)="resume.set($event)" aria-label="Resume text"></textarea>
            <span class="hint">{{ words(resume()) }} words</span>
          </div>
        </section>

        <section class="card">
          <div class="card-head"><h2>Job description</h2></div>
          <div class="card-body stack">
            <input class="input" placeholder="Job title (optional)" [ngModel]="title()" (ngModelChange)="title.set($event)" aria-label="Job title" />
            <textarea class="textarea" rows="13" [placeholder]="placeholder"
                      [ngModel]="jd()" (ngModelChange)="jd.set($event)" aria-label="Job description"></textarea>
            <span class="hint">Skills under "Nice to have", "Preferred" or "Bonus" are treated as optional.</span>
          </div>
        </section>
      </div>

      <div class="actions">
        <button class="btn btn-primary btn-lg" [disabled]="!canRun() || loading()" (click)="run()">
          @if (loading()) { <span class="spinner"></span> Comparing… } @else { Compare <app-icon name="arrow-right" [size]="16" /> }
        </button>
      </div>

      @if (result(); as res) {
        <section class="card result">
          <div class="card-head">
            <app-score-ring [value]="res.match.scores.hybrid" [size]="56" />
            <div class="spacer">
              <div class="row wrap"><h2>{{ res.match.title }}</h2>
                <span class="badge" [class]="band().cls">{{ band().label }}</span></div>
              <p>Would rank #{{ res.match.ranks.hybrid }} of {{ res.match.rank_among }} jobs in the library ·
                SBERT {{ res.match.scores.sbert | number: '1.3-3' }} · TF-IDF {{ res.match.scores.tfidf | number: '1.3-3' }}</p>
            </div>
          </div>
          <div class="card-body grid grid-2" style="gap: 28px">
            <div><h3 class="h">Score breakdown</h3><app-score-breakdown [match]="res.match" /></div>
            <div><h3 class="h">Skill gap</h3><app-gap-view [gap]="res.match.gap" /></div>
          </div>
          <div class="card-body evidence">
            <h3 class="h">Why this score</h3>
            <app-evidence-list [evidence]="res.evidence" />
          </div>
        </section>
      }
    </div>
  `,
  styles: `
    .actions { display: flex; justify-content: flex-end; margin: 16px 0 20px; }
    .h { margin-bottom: 14px; }
    .evidence { border-top: 1px solid var(--border); }
    .result .card-head p { color: var(--text-2); font-size: 13px; margin-top: 2px; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JdMatchPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected state = inject(StateService);
  private config = toSignal(this.api.config$);

  protected placeholder = 'Paste the job posting, e.g.\n\nRequirements:\n- 2+ years of Python\n- Experience with SQL\n\nNice to have:\n- Docker';
  protected resume = signal(this.state.result()?.profile.raw_text ?? '');
  protected title = signal('');
  protected jd = signal('');
  protected loading = signal(false);
  protected result = signal<CustomMatchResult | null>(null);
  protected band = computed(() => scoreBand(this.result()?.match.scores.hybrid ?? 0));
  protected canRun = computed(() => this.words(this.resume()) >= 30 && this.jd().trim().length >= 40);

  protected words(t: string) { return t.trim().split(/\s+/).filter(Boolean).length; }

  protected useCurrent() { this.resume.set(this.state.result()?.profile.raw_text ?? ''); }

  protected upload(event: Event) {
    const input = event.target as HTMLInputElement;
    const f = input.files?.[0];
    input.value = '';
    if (!f) return;
    this.api.extractText(f).subscribe({
      next: r => { this.resume.set(r.text); this.toast.info('Resume loaded', `${r.filename} · ${r.words} words`); },
      error: e => this.toast.error('Could not read the file', errorMessage(e)),
    });
  }

  protected run() {
    if (!this.canRun()) {
      this.toast.error('Missing input', 'Add a resume (30+ words) and a job description (40+ characters).');
      return;
    }
    this.loading.set(true);
    const model = this.state.result()?.settings.model ?? this.config()?.default_model ?? '';
    this.api.matchCustom(this.resume(), this.title(), this.jd(), model).subscribe({
      next: r => { this.result.set(r); this.loading.set(false); },
      error: e => { this.loading.set(false); this.toast.error('Comparison failed', errorMessage(e)); },
    });
  }
}
