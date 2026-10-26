import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import {
  AnalysisResult, AnalyzeRequest, AppConfig, CustomMatchResult, EvaluationResult, Explanation, Job, JobList, NewJob,
} from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = '/api';

  readonly config$: Observable<AppConfig> = this.http.get<AppConfig>(`${this.base}/config`).pipe(shareReplay(1));

  health() { return this.http.get<{ status: string; ready: boolean }>(`${this.base}/health`); }

  sample(name: string) { return this.http.get<{ name: string; text: string }>(`${this.base}/samples/${name}`); }

  analyze(req: AnalyzeRequest): Observable<AnalysisResult> {
    const form = new FormData();
    if (req.file) form.append('file', req.file, req.file.name);
    if (req.text) form.append('text', req.text);
    if (req.sample_name) form.append('sample_name', req.sample_name);
    form.append('method', req.method);
    form.append('model', req.model);
    form.append('top_k', String(req.top_k));
    form.append('w_semantic', String(req.weights.semantic));
    form.append('w_skills', String(req.weights.skills));
    form.append('w_experience', String(req.weights.experience));
    form.append('w_education', String(req.weights.education));
    form.append('infer_skills', String(req.infer_skills));
    return this.http.post<AnalysisResult>(`${this.base}/analyze`, form);
  }

  extractText(file: File) {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<{ filename: string; text: string; words: number }>(`${this.base}/extract-text`, form);
  }

  explain(resumeText: string, jobId: string, model: string) {
    return this.http.post<Explanation>(`${this.base}/explain`, { resume_text: resumeText, job_id: jobId, model });
  }

  matchCustom(resumeText: string, title: string, description: string, model: string) {
    return this.http.post<CustomMatchResult>(`${this.base}/match-custom`,
      { resume_text: resumeText, title, description, model });
  }

  jobs(q = '', category = '') {
    return this.http.get<JobList>(`${this.base}/jobs`, { params: { q, category } });
  }

  job(id: string) { return this.http.get<Job>(`${this.base}/jobs/${id}`); }

  addJob(job: NewJob) { return this.http.post<Job>(`${this.base}/jobs`, job); }

  deleteJob(id: string) { return this.http.delete<void>(`${this.base}/jobs/${id}`); }

  evaluation() { return this.http.get<EvaluationResult>(`${this.base}/evaluation`); }

  runEvaluation(model: string) { return this.http.post<EvaluationResult>(`${this.base}/evaluation/run`, { model }); }
}

/** Turns an HTTP error into a message suitable for a toast. */
export function errorMessage(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return 'Cannot reach the server. Make sure the API is running on port 8000.';
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join('; ');
    return `Request failed (${err.status})`;
  }
  return 'Something went wrong';
}
