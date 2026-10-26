import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService, errorMessage } from '../core/api.service';
import { Job } from '../core/models';
import { Icon } from '../shared/icon';

const PLACEHOLDER = `Responsibilities:
- Build and maintain ...

Requirements:
- 2+ years of experience with Python and SQL
- Bachelor's degree in Computer Science

Nice to have:
- Docker, AWS`;

@Component({
  selector: 'app-add-job-dialog',
  imports: [ReactiveFormsModule, Icon],
  template: `
    <form class="dialog" style="width: min(720px, 95vw)" [formGroup]="form" (ngSubmit)="save()">
      <div class="dialog-head">
        <div class="spacer"><h2>Add a job</h2>
          <p>The job is added to the library and included in every future analysis.</p></div>
        <button type="button" class="btn btn-ghost icon-btn" (click)="ref.close()" aria-label="Close"><app-icon name="x" /></button>
      </div>
      <div class="dialog-body stack" style="gap: 14px">
        <div class="grid grid-2" style="gap: 14px">
          <div class="field">
            <label for="t">Job title *</label>
            <input id="t" class="input" formControlName="title" [class.invalid]="invalid('title')" placeholder="e.g. Machine Learning Engineer" />
            @if (invalid('title')) { <span class="error-text">Enter a job title.</span> }
          </div>
          <div class="field"><label for="c">Company</label><input id="c" class="input" formControlName="company" /></div>
          <div class="field">
            <label for="cat">Category</label>
            <input id="cat" class="input" formControlName="category" list="cats" placeholder="e.g. Data Science" />
            <datalist id="cats">@for (c of data.categories; track c) { <option [value]="c"></option> }</datalist>
          </div>
          <div class="field"><label for="l">Location</label><input id="l" class="input" formControlName="location" placeholder="e.g. Lahore (Hybrid)" /></div>
        </div>
        <div class="field">
          <label for="d">Job description *</label>
          <textarea id="d" class="textarea" rows="12" formControlName="description" [placeholder]="placeholder" [class.invalid]="invalid('description')"></textarea>
          @if (invalid('description')) { <span class="error-text">The description needs at least 40 characters.</span> }
          <span class="hint">Put optional skills under a heading such as "Nice to have" or "Preferred" so they are treated as preferred.</span>
        </div>
      </div>
      <div class="dialog-foot">
        <button type="button" class="btn" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="saving()">
          @if (saving()) { <span class="spinner"></span> } Add job
        </button>
      </div>
      @if (error()) { <div class="callout warn" style="margin: 0 20px 16px"><app-icon name="alert" />{{ error() }}</div> }
    </form>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AddJobDialog {
  protected ref = inject<DialogRef<Job>>(DialogRef);
  protected data = inject<{ categories: string[] }>(DIALOG_DATA);
  private api = inject(ApiService);
  protected placeholder = PLACEHOLDER;
  protected saving = signal(false);
  protected error = signal('');
  private submitted = signal(false);

  protected form = inject(FormBuilder).nonNullable.group({
    title: ['', [Validators.required, Validators.minLength(2)]],
    company: [''],
    category: [''],
    location: [''],
    description: ['', [Validators.required, Validators.minLength(40)]],
  });

  protected invalid(name: keyof typeof this.form.controls) {
    const c = this.form.controls[name];
    return c.invalid && (c.touched || this.submitted());
  }

  protected save() {
    this.submitted.set(true);
    if (this.form.invalid) return;
    this.saving.set(true);
    this.error.set('');
    this.api.addJob(this.form.getRawValue()).subscribe({
      next: job => this.ref.close(job),
      error: e => { this.saving.set(false); this.error.set(errorMessage(e)); },
    });
  }
}
