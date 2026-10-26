import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'analyze' },
  { path: 'analyze', title: 'Analyze resume · SkillMatch', loadComponent: () => import('./pages/analyze/analyze').then(m => m.AnalyzePage) },
  { path: 'results', title: 'Results · SkillMatch', loadComponent: () => import('./pages/results/results').then(m => m.ResultsPage) },
  { path: 'jd-match', title: 'Match a job description · SkillMatch', loadComponent: () => import('./pages/jd-match/jd-match').then(m => m.JdMatchPage) },
  { path: 'jobs', title: 'Job library · SkillMatch', loadComponent: () => import('./pages/jobs/jobs').then(m => m.JobsPage) },
  { path: 'evaluation', title: 'Evaluation · SkillMatch', loadComponent: () => import('./pages/evaluation/evaluation').then(m => m.EvaluationPage) },
  { path: 'about', title: 'Methodology · SkillMatch', loadComponent: () => import('./pages/about/about').then(m => m.AboutPage) },
  { path: '**', redirectTo: 'analyze' },
];
