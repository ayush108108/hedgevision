export interface WatchItem {
  id: string; // `${asset1}-${asset2}-${granularity}`
  asset1: string;
  asset2: string;
  granularity?: string;
  notes?: string;
  addedAt: string; // ISO timestamp
}

const STORAGE_KEY = "watchlist:v1";

function readStorage(): WatchItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStorage(items: WatchItem[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function getWatchlist(): WatchItem[] {
  return readStorage();
}

export function addToWatchlist(asset1: string, asset2: string, granularity?: string, notes?: string): WatchItem[] {
  const items = readStorage();
  const id = `${asset1}-${asset2}-${granularity || "daily"}`;
  if (!items.find((i) => i.id === id)) {
    items.unshift({ id, asset1, asset2, granularity, notes, addedAt: new Date().toISOString() });
    writeStorage(items);
  }
  return items;
}

export function removeFromWatchlist(id: string): WatchItem[] {
  const items = readStorage().filter((i) => i.id !== id);
  writeStorage(items);
  return items;
}

export function clearWatchlist(): void {
  writeStorage([]);
}
