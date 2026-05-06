function getBaseUrl(): string {
  if (typeof window === "undefined") {
    return (
      process.env.INTERNAL_API_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000"
    );
  }

  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

const REQUEST_TIMEOUT_MS = 3000;

async function fetchJson<T>(path: string, init: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${getBaseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return fetchJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function get<T>(path: string): Promise<T> {
  return fetchJson<T>(path, { cache: "no-store" });
}

export const api = {
  getBrands: () => get<string[]>("/api/brands"),
  getFreshness: () => get<{ last_loaded_at: string | null; latest_post_date: string | null }>("/api/freshness"),
  getTaggers: (brands: string[], page = 1, page_size = 20) =>
    post<TaggerResponse>("/api/taggers", { brands, page, page_size }),
  getTaggerDetail: (insta_id: string, brands: string[]) =>
    get<TaggerDetail>(`/api/taggers/${encodeURIComponent(insta_id)}?brands=${brands.join(",")}`),
  getCoBrands: (brands: string[]) =>
    post<CoBrandResponse>("/api/co-brands", { brands }),
  getCoBrandDetail: (tagged_account: string, brands: string[]) =>
    get<CoBrandDetail>(`/api/co-brands/${encodeURIComponent(tagged_account)}?brands=${brands.join(",")}`),
};

export interface TaggerRow {
  rank: number;
  insta_id: string;
  insta_name: string;
  tag_count: number;
  latest_tag_date: string | null;
  other_brand_count: number;
}

export interface TaggerKpi {
  total_accounts: number;
  avg_tag_count: number;
  top_tagger_id: string | null;
  top_tagger_name: string | null;
  top_tagger_count: number;
}

export interface TaggerResponse {
  kpi: TaggerKpi;
  rows: TaggerRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaggerDetail {
  profile: { insta_id: string; display_name: string };
  top_brands: { brand: string; count: number }[];
  recent_posts: { post_id: string; post_date: string; tagged_accounts: string; full_link: string }[];
}

export interface CoBrandRow {
  rank: number;
  tagged_account: string;
  tagger_count: number;
  total_tag_count: number;
  tagger_ratio: number;
}

export interface CoBrandResponse {
  kpi: { total_accounts: number; co_brand_count: number };
  rows: CoBrandRow[];
}

export interface CoBrandDetail {
  taggers: { insta_id: string; display_name: string; tag_count: number; latest_tag_date: string }[];
  monthly: { month: string; tagger_count: number }[];
}
