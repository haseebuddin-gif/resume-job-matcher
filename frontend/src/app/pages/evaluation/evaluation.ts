import { DecimalPipe, KeyValuePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ApiService, errorMessage } from '../../core/api.service';
import { EvaluationResult, Method, RankingMetrics } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { Icon } from '../../shared/icon';
import { Bar, MethodBars } from '../../shared/method-bars';

const METHODS: { id: Method; short: string; long: string }[] = [
  { id: 'tfidf', short: 'TF-IDF', long: 'TF-IDF + cosine (baseline)' },
  { id: 'sbert', short: 'SBERT', long: 'SBERT + cosine (proposed)' },
  { id: 'hybrid', short: 'Hybrid', long: 'Hybrid: SBERT + skills + experience + education' },
];
const CHART_METRICS = ['MRR', 'P@3', 'nDCG@5', 'Recall@3'];

@Component({
  selector: 'app-evaluation-page',
  imports: [FormsModule, Icon, MethodBars, DecimalPipe, KeyValuePipe],
  templateUrl: './evaluation.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: `
    .charts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 24px; }
    @media (max-width: 1100px) { .charts { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 640px) { .charts { grid-template-columns: 1fr; } }
    .meta { display: flex; gap: 22px; flex-wrap: wrap; font-size: 13px; color: var(--text-2); }
    .meta strong { color: var(--text); font-weight: 600; }
    section { margin-bottom: 18px; }
    td.best { font-weight: 700; color: var(--accent-text); }
  `,
})
export class EvaluationPage {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  protected config = toSignal(this.api.config$);
  protected readonly methods = METHODS;

  protected result = signal<EvaluationResult | null>(null);
  protected loading = signal(true);
  protected running = signal(false);
  protected model = signal('');

  protected metricKeys = computed(() => {
    const r = this.result();
    return r ? Object.keys(r.ranking.hybrid).filter(k => k !== 'queries') : [];
  });
  protected charts = computed(() => {
    const r = this.result();
    if (!r) return [];
    return CHART_METRICS.map(metric => ({
      metric,
      bars: METHODS.map<Bar>(m => ({ label: m.short, value: r.ranking[m.id][metric] ?? 0 })),
    }));
  });

  constructor() {
    effect(() => {
      const cfg = this.config();
      if (cfg && !this.model()) this.model.set(cfg.default_model);
    });
    this.api.evaluation().subscribe({
      next: r => { this.result.set(r); this.loading.set(false); },
      error: () => this.loading.set(false), // 404 = not run yet
    });
  }

  protected best(metric: string): number {
    const r = this.result();
    return r ? Math.max(...METHODS.map(m => r.ranking[m.id][metric] ?? 0)) : 0;
  }

  protected bestIn(table: Record<string, RankingMetrics>, metric: string): number {
    return Math.max(...Object.values(table).map(v => v[metric] ?? 0));
  }

  protected run() {
    this.running.set(true);
    this.api.runEvaluation(this.model()).subscribe({
      next: r => {
        this.result.set(r);
        this.running.set(false);
        this.toast.success('Evaluation finished', `${r.ranking.hybrid['queries']} resumes, ${r.n_jobs} jobs`);
      },
      error: e => { this.running.set(false); this.toast.error('Evaluation failed', errorMessage(e)); },
    });
  }

  protected methodLabel(id: string) { return METHODS.find(m => m.id === id)?.long ?? id; }
  protected modelName(id: string) { return id.split('/').pop(); }
}
