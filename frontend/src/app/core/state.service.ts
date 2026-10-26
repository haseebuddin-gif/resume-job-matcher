import { Injectable, computed, signal } from '@angular/core';
import { AnalysisResult } from './models';

export interface HistoryEntry {
  id: string;
  date: string;
  name: string;
  source: string;
  topJob: string;
  topScore: number;
  result: AnalysisResult;
}

const CURRENT_KEY = 'rjm.current';
const HISTORY_KEY = 'rjm.history';
const HISTORY_LIMIT = 6;

function read<T>(key: string, store: Storage, fallback: T): T {
  try {
    const raw = store.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, store: Storage, value: unknown) {
  try {
    store.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the app still works without persistence */
  }
}

/** Holds the current analysis and a short local history (browser storage only). */
@Injectable({ providedIn: 'root' })
export class StateService {
  readonly result = signal<AnalysisResult | null>(read(CURRENT_KEY, sessionStorage, null));
  readonly history = signal<HistoryEntry[]>(read(HISTORY_KEY, localStorage, []));
  readonly hasResult = computed(() => this.result() !== null);

  setResult(result: AnalysisResult) {
    this.result.set(result);
    write(CURRENT_KEY, sessionStorage, result);
    const top = result.matches[0];
    const entry: HistoryEntry = {
      id: crypto.randomUUID(),
      date: new Date().toISOString(),
      name: result.profile.name || 'Unnamed candidate',
      source: result.settings.source,
      topJob: top ? top.title : '-',
      topScore: top ? top.scores.match : 0,
      result,
    };
    this.history.update(h => [entry, ...h].slice(0, HISTORY_LIMIT));
    write(HISTORY_KEY, localStorage, this.history());
  }

  open(entry: HistoryEntry) {
    this.result.set(entry.result);
    write(CURRENT_KEY, sessionStorage, entry.result);
  }

  removeHistory(id: string) {
    this.history.update(h => h.filter(e => e.id !== id));
    write(HISTORY_KEY, localStorage, this.history());
  }
}
