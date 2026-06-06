import type { Table } from "dexie";

const SYNC_KEY_PREFIX = "airunner:sync:";

// ── SyncManager ──────────────────────────────────────────────────────────────
//
// Generic cache manager that:
//  1. Serves cached records immediately (readCached)
//  2. Fetches from server, merges into IndexedDB (sync)
//  3. Tracks last-sync timestamp in localStorage for future delta fetches
//
// The serverFetch function may receive an ISO timestamp string to request
// only records updated after that point; servers that ignore it return all
// records (safe — bulkPut handles merging).

export class SyncManager<T extends Record<string, unknown>> {
  private readonly syncKey: string;

  constructor(
    private readonly table: Table<T, unknown>,
    private readonly serverFetch: (since?: string) => Promise<T[]>,
    syncKey: string,
  ) {
    this.syncKey = SYNC_KEY_PREFIX + syncKey;
  }

  readCached(): Promise<T[]> {
    return this.table.toArray();
  }

  async sync(): Promise<T[]> {
    const lastSynced = this.getLastSynced();
    const fresh = await this.serverFetch(lastSynced ?? undefined);
    if (fresh.length > 0) {
      await this.table.bulkPut(fresh);
    }
    this.setLastSynced(new Date().toISOString());
    return this.table.toArray();
  }

  async invalidate(): Promise<void> {
    await this.table.clear();
    localStorage.removeItem(this.syncKey);
  }

  getLastSynced(): string | null {
    try {
      return localStorage.getItem(this.syncKey);
    } catch {
      return null;
    }
  }

  setLastSynced(ts: string): void {
    try {
      localStorage.setItem(this.syncKey, ts);
    } catch { /* quota */ }
  }
}
