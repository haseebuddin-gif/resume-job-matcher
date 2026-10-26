import { Dialog } from '@angular/cdk/dialog';
import { ComponentType } from '@angular/cdk/portal';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfirmData, ConfirmDialog } from './confirm.dialog';
import { TextPreviewData, TextPreviewDialog } from './text-preview.dialog';

/** Thin wrapper around CDK Dialog so every popup shares backdrop, focus and close behaviour. */
@Injectable({ providedIn: 'root' })
export class Dialogs {
  private dialog = inject(Dialog);

  open<R, D, C>(component: ComponentType<C>, data: D): Observable<R | undefined> {
    return this.dialog.open<R, D, C>(component, {
      data,
      panelClass: 'app-dialog',
      backdropClass: 'cdk-overlay-dark-backdrop',
      autoFocus: 'first-tabbable',
      restoreFocus: true,
    }).closed;
  }

  confirm(data: ConfirmData) { return this.open<boolean, ConfirmData, ConfirmDialog>(ConfirmDialog, data); }

  preview(data: TextPreviewData) { return this.open<boolean, TextPreviewData, TextPreviewDialog>(TextPreviewDialog, data); }
}
