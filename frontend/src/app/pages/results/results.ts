import { DecimalPipe, KeyValuePipe, PercentPipe, TitleCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { JobMatch, Quality, Recommendation } from '../../core/models';
import { StateService } from '../../core/state.service';
import { Dialogs } from '../../dialogs/dialogs';
import { JobMatchData, JobMatchDialog } from '../../dialogs/job-match.dialog';
import { QualityDialog } from '../../dialogs/quality.dialog';
import { GapView } from '../../shared/gap-view';
import { Icon } from '../../shared/icon';
import { ScoreRing, scoreBand } from '../../shared/score-ring';

type Tab = 'matches' | 'gap' | 'profile' | 'compare';
type SortKey = 'hybrid_rank' | 'sbert_rank' | 'tfidf_rank';

const METHOD_LABEL = { hybrid: 'Hybrid score', sbert: 'SBERT similarity', tfidf: 'TF-IDF baseline' };
const PHASES: Recommendation['phase'][] = ['Focus now', 'Next', 'Later'];

@Component({
  selector: 'app-results-page',
  imports: [RouterLink, Icon, ScoreRing, GapView, DecimalPipe, PercentPipe, TitleCasePipe, KeyValuePipe],
  templateUrl: './results.html',
  styleUrl: './results.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsPage {
  protected state = inject(StateService);
  private dialogs = inject(Dialogs);

  protected r = this.state.result;
  protected tab = signal<Tab>('matches');
  protected sortKey = signal<SortKey>('hybrid_rank');
  protected gapJobId = signal<string>('');
  protected readonly phases = PHASES;
  protected readonly methodLabel = METHOD_LABEL;
  protected readonly band = scoreBand;

  protected best = computed(() => this.r()?.matches[0] ?? null);
  protected skillCount = computed(() => {
    const p = this.r()?.profile;
    return p ? p.skills.length + p.inferred_skills.length : 0;
  });
  protected roadmap = computed(() => {
    const recs = this.r()?.recommendations ?? [];
    return PHASES.map(phase => ({ phase, items: recs.filter(x => x.phase === phase) }));
  });
  protected gapJob = computed(() => {
    const matches = this.r()?.matches ?? [];
    return matches.find(m => m.job_id === this.gapJobId()) ?? matches[0] ?? null;
  });
  protected compareRows = computed(() => {
    const rows = [...(this.r()?.comparison.rows ?? [])];
    const k = this.sortKey();
    return rows.sort((a, b) => a[k] - b[k]);
  });
  protected sections = computed(() =>
    Object.entries(this.r()?.profile.sections ?? {}).filter(([name]) => name !== 'header'));
  protected categoryCount = computed(() => Object.keys(this.r()?.profile.skills_by_category ?? {}).length);
  protected maxPriority = computed(() => Math.max(1, ...(this.r()?.recommendations ?? []).map(x => x.priority)));

  protected openMatch(m: JobMatch) {
    const r = this.r()!;
    this.dialogs.open<void, JobMatchData, JobMatchDialog>(JobMatchDialog, {
      match: m,
      resumeText: r.profile.raw_text,
      model: r.settings.model,
      weights: r.settings.method === 'hybrid' ? r.settings.weights : null,
      candidateName: r.profile.name,
      candidateYears: r.profile.experience_years,
    }).subscribe();
  }

  protected openQuality() {
    this.dialogs.open<void, Quality, QualityDialog>(QualityDialog, this.r()!.quality).subscribe();
  }

  protected showSource() {
    const p = this.r()!.profile;
    this.dialogs.preview({ title: 'Extracted resume text', subtitle: 'Plain text read from the uploaded file', text: p.raw_text }).subscribe();
  }

  protected print() { window.print(); }

  protected rankDelta(a: number, b: number) { return b - a; }

  protected topBy(key: SortKey) {
    return this.r()?.comparison.rows.find(row => row[key] === 1)?.title ?? '—';
  }

  protected modelName(id: string) { return id.split('/').pop(); }
}
