import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ToastService } from '../core/toast.service';
import { Icon } from './icon';

@Component({
  selector: 'app-toasts',
  imports: [Icon],
  template: `
    <div class="toasts" aria-live="polite">
      @for (t of toast.toasts(); track t.id) {
        <div class="toast" [class]="t.kind" role="status">
          <app-icon [name]="t.kind === 'success' ? 'check-circle' : t.kind === 'error' ? 'x-circle' : 'info'" [size]="18" />
          <div class="body">
            <strong>{{ t.title }}</strong>
            @if (t.message) { <p>{{ t.message }}</p> }
          </div>
          <button class="btn btn-ghost icon-btn" (click)="toast.dismiss(t.id)" aria-label="Dismiss">
            <app-icon name="x" [size]="14" />
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    .toasts { position: fixed; right: 20px; bottom: 20px; z-index: 2000; display: flex; flex-direction: column; gap: 10px; width: min(380px, calc(100vw - 32px)); }
    .toast { display: flex; gap: 10px; align-items: flex-start; padding: 12px 10px 12px 14px; background: var(--surface); border: 1px solid var(--border);
             border-radius: 10px; box-shadow: var(--shadow-md); animation: in .18s ease-out; border-left: 3px solid var(--accent); }
    .toast.success { border-left-color: var(--good); } .toast.success app-icon { color: var(--good); }
    .toast.error { border-left-color: var(--bad); } .toast.error app-icon { color: var(--bad); }
    .toast.info app-icon { color: var(--accent); }
    .body { flex: 1; min-width: 0; padding-top: 1px; }
    strong { font-weight: 600; }
    p { color: var(--text-2); font-size: 13px; margin-top: 2px; }
    .icon-btn { width: 26px; height: 26px; }
    @keyframes in { from { opacity: 0; transform: translateY(6px); } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Toasts {
  protected toast = inject(ToastService);
}
