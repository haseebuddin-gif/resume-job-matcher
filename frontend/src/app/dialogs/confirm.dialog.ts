import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

export interface ConfirmData { title: string; message: string; confirmLabel?: string; danger?: boolean; }

@Component({
  selector: 'app-confirm-dialog',
  template: `
    <div class="dialog" style="width: min(440px, 92vw)" role="alertdialog" aria-modal="true">
      <div class="dialog-head"><h2>{{ data.title }}</h2></div>
      <div class="dialog-body"><p class="text-2">{{ data.message }}</p></div>
      <div class="dialog-foot">
        <button class="btn" (click)="ref.close(false)">Cancel</button>
        <button class="btn" [class.btn-primary]="!data.danger" [class.btn-danger]="data.danger" [class.solid]="data.danger"
                (click)="ref.close(true)">{{ data.confirmLabel || 'Confirm' }}</button>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfirmDialog {
  protected ref = inject<DialogRef<boolean>>(DialogRef);
  protected data = inject<ConfirmData>(DIALOG_DATA);
}
