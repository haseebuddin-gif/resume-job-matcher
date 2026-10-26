import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { StateService } from '../core/state.service';
import { Icon } from './icon';

type Theme = 'light' | 'dark';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, Icon],
  template: `
    <aside class="sidebar">
      <a routerLink="/analyze" class="brand">
        <span class="logo"><app-icon name="target" [size]="18" [stroke]="2" /></span>
        <span><strong>SkillMatch</strong><small>Resume–job matching</small></span>
      </a>

      <nav>
        <span class="nav-label">Workspace</span>
        <a routerLink="/analyze" routerLinkActive="active"><app-icon name="upload" />Analyze resume</a>
        <a routerLink="/results" routerLinkActive="active">
          <app-icon name="layers" />Results
          @if (state.hasResult()) { <span class="dot" aria-label="results available"></span> }
        </a>
        <a routerLink="/jd-match" routerLinkActive="active"><app-icon name="compare" />Match a job description</a>
        <a routerLink="/jobs" routerLinkActive="active"><app-icon name="briefcase" />Job library</a>

        <span class="nav-label">Research</span>
        <a routerLink="/evaluation" routerLinkActive="active"><app-icon name="chart" />Evaluation</a>
        <a routerLink="/about" routerLinkActive="active"><app-icon name="book" />Methodology</a>
      </nav>

      <div class="foot">
        <button class="btn btn-ghost btn-sm" (click)="toggleTheme()">
          <app-icon [name]="theme() === 'dark' ? 'sun' : 'moon'" [size]="15" />
          {{ theme() === 'dark' ? 'Light' : 'Dark' }} mode
        </button>
        <p>Open-source NLP · runs locally</p>
      </div>
    </aside>
  `,
  styles: `
    :host { position: fixed; inset: 0 auto 0 0; width: var(--sidebar); z-index: 10; }
    .sidebar { height: 100%; display: flex; flex-direction: column; background: var(--surface); border-right: 1px solid var(--border); padding: 16px 12px; }
    .brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 18px; color: var(--text); text-decoration: none; }
    .brand strong { display: block; font-size: 15px; letter-spacing: -0.01em; }
    .brand small { display: block; font-size: 11.5px; color: var(--muted); }
    .logo { width: 32px; height: 32px; border-radius: 8px; display: grid; place-items: center; background: var(--accent); color: #fff; }
    nav { display: flex; flex-direction: column; gap: 2px; }
    .nav-label { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); padding: 14px 10px 6px; }
    nav a { display: flex; align-items: center; gap: 10px; height: 34px; padding: 0 10px; border-radius: 7px; color: var(--text-2); font-weight: 520; text-decoration: none; }
    nav a:hover { background: var(--surface-2); color: var(--text); }
    nav a.active { background: var(--accent-weak); color: var(--accent-text); }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--good); margin-left: auto; }
    .foot { margin-top: auto; padding: 8px; display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
    .foot p { font-size: 11.5px; color: var(--muted); padding-left: 10px; }
    @media (max-width: 900px) {
      :host { position: sticky; top: 0; inset: auto; width: auto; }
      .sidebar { flex-direction: row; align-items: center; height: auto; padding: 8px 12px; border-right: 0; border-bottom: 1px solid var(--border); overflow-x: auto; }
      .brand { padding: 0 8px 0 0; } .brand small, .nav-label, .foot { display: none; }
      nav { flex-direction: row; } nav a { white-space: nowrap; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sidebar {
  protected state = inject(StateService);
  protected theme = signal<Theme>(this.initialTheme());

  private initialTheme(): Theme {
    let saved: string | null = null;
    try { saved = localStorage.getItem('rjm.theme'); } catch { /* storage blocked */ }
    const theme: Theme = saved === 'dark' || saved === 'light'
      ? saved : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.dataset['theme'] = theme;
    return theme;
  }

  toggleTheme() {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    document.documentElement.dataset['theme'] = next;
    try { localStorage.setItem('rjm.theme', next); } catch { /* storage blocked */ }
  }
}
