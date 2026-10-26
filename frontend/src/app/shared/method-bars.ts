import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export interface Bar { label: string; value: number; }

/** One metric, one bar per method. Single hue: the best method is accent, the rest neutral, values labelled directly. */
@Component({
  selector: 'app-method-bars',
  imports: [DecimalPipe],
  template: `
    <figure>
      <figcaption>{{ title() }}</figcaption>
      @for (b of bars(); track b.label) {
        <div class="bar-row" [attr.title]="b.label + ': ' + (b.value | number: '1.3-3')">
          <span class="lbl">{{ b.label }}</span>
          <div class="track"><div class="fill" [class.best]="b.value === best() && best() > 0" [style.width.%]="b.value * 100"></div></div>
          <span class="val tnum">{{ b.value | number: '1.3-3' }}</span>
        </div>
      }
    </figure>
  `,
  styles: `
    figure { margin: 0; }
    figcaption { font-weight: 600; font-size: 13.5px; margin-bottom: 12px; }
    .bar-row { display: grid; grid-template-columns: 70px 1fr 46px; gap: 10px; align-items: center; margin-bottom: 8px; }
    .lbl { font-size: 12.5px; color: var(--text-2); }
    .track { height: 14px; background: var(--surface-2); border-radius: 4px; overflow: hidden; }
    .fill { height: 100%; background: var(--border-strong); border-radius: 0 4px 4px 0; transition: width .5s ease; }
    .fill.best { background: var(--accent); }
    .val { font-size: 12.5px; font-weight: 600; text-align: right; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MethodBars {
  readonly title = input.required<string>();
  readonly bars = input.required<Bar[]>();
  protected best = computed(() => Math.max(...this.bars().map(b => b.value)));
}
