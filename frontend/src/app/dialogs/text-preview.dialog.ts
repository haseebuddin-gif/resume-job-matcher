import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Icon } from '../shared/icon';

export interface TextPreviewData { title: string; subtitle?: string; text: string; actionLabel?: string; }

@Component({
  selector: 'app-text-preview-dialog',
  imports: [Icon],
  template: `
    <div class="dialog" style="width: min(760px, 94vw)">
      <div class="dialog-head">
        <div class="spacer">
          <h2>{{ data.title }}</h2>
          @if (data.subtitle) { <p>{{ data.subtitle }}</p> }
        </div>
        <button class="btn btn-ghost icon-btn" (click)="ref.close()" aria-label="Close"><app-icon name="x" /></button>
      </div>
      <div class="dialog-body"><pre class="preview">{{ data.text }}</pre></div>
      <div class="dialog-foot">
        <button class="btn" (click)="ref.close()">Close</button>
        @if (data.actionLabel) {
          <button class="btn btn-primary" (click)="ref.close(true)">{{ data.actionLabel }}</button>
        }
      </div>
    </div>
  `,
  styles: `.preview { margin: 0; white-space: pre-wrap; font: 13px/1.6 inherit; font-family: inherit; color: var(--text-2); }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TextPreviewDialog {
  protected ref = inject<DialogRef<boolean>>(DialogRef);
  protected data = inject<TextPreviewData>(DIALOG_DATA);
}
