import { Injectable, signal } from '@angular/core';

export type ToastKind = 'success' | 'error' | 'info';
export interface Toast { id: number; kind: ToastKind; title: string; message?: string; }

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private nextId = 1;

  show(kind: ToastKind, title: string, message?: string, timeout = 4500) {
    const id = this.nextId++;
    this.toasts.update(t => [...t, { id, kind, title, message }]);
    if (timeout) setTimeout(() => this.dismiss(id), timeout);
  }

  success(title: string, message?: string) { this.show('success', title, message); }
  error(title: string, message?: string) { this.show('error', title, message, 7000); }
  info(title: string, message?: string) { this.show('info', title, message); }

  dismiss(id: number) { this.toasts.update(t => t.filter(x => x.id !== id)); }
}
