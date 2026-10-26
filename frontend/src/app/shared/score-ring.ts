import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/** Circular gauge for a 0-1 score. Colour reflects the band (strong / moderate / weak). */
@Component({
  selector: 'app-score-ring',
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 40 40" role="img"
         [attr.aria-label]="(label() || 'Score') + ' ' + percent() + '%'">
      <circle cx="20" cy="20" r="16" fill="none" stroke="var(--surface-3)" stroke-width="3.5" />
      <circle cx="20" cy="20" r="16" fill="none" [attr.stroke]="color()" stroke-width="3.5" stroke-linecap="round"
              [attr.stroke-dasharray]="dash()" transform="rotate(-90 20 20)" class="arc" />
      <text x="20" y="20" text-anchor="middle" dominant-baseline="central" class="val">{{ percent() }}</text>
    </svg>
    @if (label()) { <span class="lbl">{{ label() }}</span> }
  `,
  styles: `
    :host { display: inline-flex; flex-direction: column; align-items: center; gap: 4px; }
    .arc { transition: stroke-dasharray .5s ease; }
    .val { font-size: 11px; font-weight: 650; fill: var(--text); font-variant-numeric: tabular-nums; }
    .lbl { font-size: 11.5px; color: var(--muted); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScoreRing {
  readonly value = input.required<number>();
  readonly size = input(52);
  readonly label = input('');

  protected readonly percent = computed(() => Math.round(Math.max(0, Math.min(1, this.value())) * 100));
  protected readonly dash = computed(() => {
    const c = 2 * Math.PI * 16;
    return `${(this.percent() / 100) * c} ${c}`;
  });
  protected readonly color = computed(() =>
    this.percent() >= 65 ? 'var(--good)' : this.percent() >= 45 ? 'var(--accent)' : 'var(--warn)');
}

/** Band label used next to scores. */
export function scoreBand(v: number): { label: string; cls: string } {
  if (v >= 0.65) return { label: 'Strong match', cls: 'good' };
  if (v >= 0.45) return { label: 'Moderate match', cls: 'accent' };
  return { label: 'Weak match', cls: 'warn' };
}
