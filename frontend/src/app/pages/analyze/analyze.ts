import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, errorMessage } from '../../core/api.service';
import { Method, Weights } from '../../core/models';
import { HistoryEntry, StateService } from '../../core/state.service';
import { ToastService } from '../../core/toast.service';
import { Dialogs } from '../../dialogs/dialogs';
import { Icon } from '../../shared/icon';

type Source = 'upload' | 'sample' | 'paste';
const ACCEPTED = ['.pdf', '.docx', '.txt'];
const MAX_BYTES = 5 * 1024 * 1024;

const SAMPLE_LABELS: Record<string, string> = {
  'business_analyst.txt': 'Business Analyst',
  'data_scientist.txt': 'Data Scientist',
  'devops.txt': 'DevOps Engineer',
  'dotnet_angular_dev.txt': '.NET / Angular Developer',
  'fresh_python_grad.txt': 'Fresh Graduate (Python)',
  'frontend_react.txt': 'Frontend Developer (React)',
  'hr_executive.txt': 'HR Executive',
  'qa_automation.txt': 'QA Automation Engineer',
};

const METHOD_INFO: Record<Method, { title: string; text: string }> = {
  hybrid: { title: 'Hybrid (recommended)', text: 'Semantic similarity combined with skill coverage, experience and education fit.' },
  sbert: { title: 'Semantic only (SBERT)', text: 'Cosine similarity of Sentence-BERT embeddings.' },
  tfidf: { title: 'Keyword baseline (TF-IDF)', text: 'Traditional vector-space matching on keywords.' },
};

@Component({
  selector: 'app-analyze-page',
  imports: [FormsModule, Icon, DatePipe, DecimalPipe, PercentPipe],
  templateUrl: './analyze.html',
  styleUrl: './analyze.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AnalyzePage {
  private api = inject(ApiService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private dialogs = inject(Dialogs);
  private destroyRef = inject(DestroyRef);
  protected state = inject(StateService);

  protected config = toSignal(this.api.config$);
  protected readonly methodInfo = METHOD_INFO;
  protected readonly methods: Method[] = ['hybrid', 'sbert', 'tfidf'];
  protected readonly weightFields: { key: keyof Weights; label: string }[] = [
    { key: 'semantic', label: 'Semantic similarity' },
    { key: 'skills', label: 'Skill coverage' },
    { key: 'experience', label: 'Experience fit' },
    { key: 'education', label: 'Education fit' },
  ];

  protected source = signal<Source>('upload');
  protected file = signal<File | null>(null);
  protected dragging = signal(false);
  protected sample = signal<string>('');
  protected pasted = signal('');

  protected method = signal<Method>('hybrid');
  protected model = signal('');
  protected topK = signal(10);
  protected weights = signal<Weights>({ semantic: 0.45, skills: 0.35, experience: 0.1, education: 0.1 });
  protected inferSkills = signal(false);
  protected showAdvanced = signal(false);

  protected loading = signal(false);
  protected serverState = signal<'checking' | 'ready' | 'warming' | 'down'>('checking');

  protected pastedWords = computed(() => this.pasted().trim().split(/\s+/).filter(Boolean).length);
  protected weightTotal = computed(() => Object.values(this.weights()).reduce((a, b) => a + b, 0));
  protected canAnalyze = computed(() => {
    if (this.loading() || this.serverState() === 'down') return false;
    switch (this.source()) {
      case 'upload': return this.file() !== null;
      case 'sample': return !!this.sample();
      case 'paste': return this.pastedWords() >= 30;
    }
  });

  constructor() {
    effect(() => {
      const cfg = this.config();
      if (cfg && !this.model()) {
        this.model.set(cfg.default_model);
        this.weights.set({ ...cfg.default_weights });
      }
    });
    this.checkServer();
  }

  private checkServer() {
    this.api.health().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: h => {
        this.serverState.set(h.ready ? 'ready' : 'warming');
        if (!h.ready) setTimeout(() => this.checkServer(), 4000);
      },
      error: () => this.serverState.set('down'),
    });
  }

  protected retryServer() {
    this.serverState.set('checking');
    this.checkServer();
  }

  // ---------------------------------------------------------------- file handling
  protected onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragging.set(false);
    const f = event.dataTransfer?.files?.[0];
    if (f) this.pickFile(f);
  }

  protected onFileInput(event: Event) {
    const input = event.target as HTMLInputElement;
    const f = input.files?.[0];
    if (f) this.pickFile(f);
    input.value = '';
  }

  private pickFile(f: File) {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      this.toast.error('Unsupported file type', 'Please upload a PDF, DOCX or TXT file.');
      return;
    }
    if (f.size > MAX_BYTES) {
      this.toast.error('File too large', 'The maximum size is 5 MB.');
      return;
    }
    this.file.set(f);
  }

  protected fileSize(bytes: number) {
    return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  protected sampleLabel(name: string) {
    return SAMPLE_LABELS[name] ?? name.replace('.txt', '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  protected previewSample(name: string, event: Event) {
    event.stopPropagation();
    this.api.sample(name).subscribe({
      next: s => this.dialogs.preview({ title: this.sampleLabel(name), subtitle: 'Sample resume (fictional)', text: s.text, actionLabel: 'Use this resume' })
        .subscribe(use => { if (use) this.sample.set(name); }),
      error: e => this.toast.error('Could not load sample', errorMessage(e)),
    });
  }

  protected setWeight(key: keyof Weights, value: number) {
    this.weights.update(w => ({ ...w, [key]: value }));
  }

  protected resetWeights() {
    const cfg = this.config();
    if (cfg) this.weights.set({ ...cfg.default_weights });
  }

  protected weightShare(key: keyof Weights) {
    const total = this.weightTotal();
    return total ? this.weights()[key] / total : 0;
  }

  // ---------------------------------------------------------------- analyze
  protected analyze() {
    if (!this.canAnalyze()) return;
    if (this.method() === 'hybrid' && this.weightTotal() === 0) {
      this.toast.error('Invalid weights', 'At least one hybrid weight must be above zero.');
      return;
    }
    this.loading.set(true);
    const src = this.source();
    this.api.analyze({
      file: src === 'upload' ? this.file() : null,
      sample_name: src === 'sample' ? this.sample() : undefined,
      text: src === 'paste' ? this.pasted() : undefined,
      method: this.method(),
      model: this.model(),
      top_k: this.topK(),
      weights: this.weights(),
      infer_skills: this.inferSkills(),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        this.loading.set(false);
        this.state.setResult(result);
        const top = result.matches[0];
        this.toast.success('Analysis complete', top ? `Best match: ${top.title}` : undefined);
        this.router.navigate(['/results']);
      },
      error: err => {
        this.loading.set(false);
        this.toast.error('Analysis failed', errorMessage(err));
      },
    });
  }

  protected openHistory(entry: HistoryEntry) {
    this.state.open(entry);
    this.router.navigate(['/results']);
  }
}
