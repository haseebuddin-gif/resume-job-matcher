export interface ModelOption { id: string; label: string; }
export interface MethodOption { id: Method; label: string; }
export type Method = 'hybrid' | 'sbert' | 'tfidf';

export interface Weights { semantic: number; skills: number; experience: number; education: number; }

export interface AppConfig {
  models: ModelOption[];
  default_model: string;
  methods: MethodOption[];
  default_weights: Weights;
  samples: string[];
}

export interface PartialMatch { job_skill: string; candidate_skill: string; similarity: number; type: 'required' | 'preferred'; }

export interface Gap {
  matched_required: string[];
  matched_preferred: string[];
  partial: PartialMatch[];
  missing_required: string[];
  missing_preferred: string[];
  skill_score: number | null;
}

export interface Scores {
  match: number; hybrid: number; semantic: number; sbert: number; tfidf: number;
  skill: number | null; experience: number; education: number;
}

export interface JobMatch {
  rank: number;
  job_id: string;
  title: string;
  company: string;
  category: string;
  location: string;
  required_skills: string[];
  preferred_skills: string[];
  min_years: number;
  required_degree: string;
  scores: Scores;
  ranks: { tfidf: number; sbert: number; hybrid: number };
  gap: Gap;
  rank_among?: number;
}

export interface InferredSkill { skill: string; evidence: string; similarity: number; category: string; }

export interface Profile {
  name: string;
  email: string;
  phone: string;
  links: string[];
  highest_degree: string;
  experience_years: number;
  education: { degree: string; details: string; year: string }[];
  skills: string[];
  inferred_skills: InferredSkill[];
  skills_by_category: Record<string, string[]>;
  sections: Record<string, string>;
  raw_text: string;
}

export interface QualityCheck { id: string; label: string; weight: number; passed: boolean; tip: string | null; }
export interface Quality {
  score: number;
  grade: string;
  stats: { words: number; bullets: number; quantified_bullets: number; action_verb_bullets: number };
  checks: QualityCheck[];
}

export interface Recommendation {
  skill: string; category: string; priority: number; needed_by: number; jobs: string[];
  advice: string; related_to: string; phase: 'Focus now' | 'Next' | 'Later';
}

export interface ComparisonRow {
  job_id: string; title: string; company: string;
  tfidf_rank: number; sbert_rank: number; hybrid_rank: number;
  tfidf_score: number; sbert_score: number; hybrid_score: number;
}

export interface AnalysisResult {
  profile: Profile;
  quality: Quality;
  matches: JobMatch[];
  comparison: { spearman: number | null; rows: ComparisonRow[] };
  recommendations: Recommendation[];
  settings: { method: Method; model: string; top_k: number; infer_skills: boolean; weights: Weights; source: string };
}

export interface Evidence { job_requirement: string; resume_evidence: string; similarity: number; }
export interface Explanation { evidence: Evidence[]; keywords: string[]; }

export interface Job {
  job_id: string; title: string; company: string; category: string; location: string; description: string;
  required_skills: string[]; preferred_skills: string[]; min_years: number; required_degree: string;
  source: 'builtin' | 'custom';
}
export interface JobList { total: number; categories: string[]; jobs: Job[]; }
export interface NewJob { title: string; company: string; category: string; location: string; description: string; }

export interface CustomMatchResult { match: JobMatch; evidence: Evidence[]; candidate_skills: string[]; }

export interface PRF {
  micro_precision: number; micro_recall: number; micro_f1: number;
  macro_precision: number; macro_recall: number; macro_f1: number;
}
export type RankingMetrics = Record<string, number>;
export interface EvaluationResult {
  timestamp: string; model: string; n_jobs: number; dataset: string;
  extraction?: PRF;
  extraction_ablation?: Record<string, PRF>;
  extraction_per_resume?: Record<string, { missed: string[]; extra: string[] }>;
  ranking: Record<Method, RankingMetrics>;
  model_comparison?: Record<string, Record<Method, RankingMetrics>>;
}

export interface AnalyzeRequest {
  file?: File | null;
  text?: string;
  sample_name?: string;
  method: Method;
  model: string;
  top_k: number;
  weights: Weights;
  infer_skills: boolean;
}
