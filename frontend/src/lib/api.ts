import type {
  AIEvent,
  AIQuery,
  Analytics,
  ChatResponse,
  HistoryItem,
  ImportJob,
  ListDetail,
  ListSummary,
  Movie,
  MovieDetail,
  ReviewItem,
  TasteProfile,
  User,
  WatchlistItem,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json();
}

export const api = {
  syncUser: (displayName?: string) =>
    fetchApi<User>("/auth/sync", {
      method: "POST",
      body: JSON.stringify({ display_name: displayName }),
    }),
  getMe: () => fetchApi<User>("/auth/me"),

  searchMovies: (q: string) => fetchApi<Movie[]>(`/movies/search?q=${encodeURIComponent(q)}`),
  getMovie: (id: number) => fetchApi<MovieDetail>(`/movies/${id}`),
  getSimilar: (id: number) => fetchApi<Movie[]>(`/movies/${id}/similar`),

  getHistory: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return fetchApi<HistoryItem[]>(`/history/${qs}`);
  },
  getTopRated: () => fetchApi<HistoryItem[]>("/history/top-rated"),

  getTaste: () => fetchApi<TasteProfile>("/profile/taste"),
  getAnalytics: () => fetchApi<Analytics>("/profile/analytics"),
  refreshTaste: () => fetchApi<TasteProfile>("/profile/taste/refresh", { method: "POST" }),

  chat: (message: string) =>
    fetchApi<ChatResponse>("/recommendations/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  getReviews: () => fetchApi<ReviewItem[]>("/reviews/feed"),
  getWatchlist: () => fetchApi<WatchlistItem[]>("/watchlist/"),
  addToWatchlist: (movieId: number) =>
    fetchApi<WatchlistItem>("/watchlist/", {
      method: "POST",
      body: JSON.stringify({ movie_id: movieId }),
    }),
  removeFromWatchlist: (itemId: number) =>
    fetchApi(`/watchlist/${itemId}`, { method: "DELETE" }),

  getLists: () => fetchApi<ListSummary[]>("/lists/"),
  getList: (id: number) => fetchApi<ListDetail>(`/lists/${id}`),

  importLetterboxd: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetchApi<ImportJob>("/import/letterboxd", { method: "POST", body: form });
  },
  getImportJobs: () => fetchApi<ImportJob[]>("/import/jobs"),
  getImportJob: (id: number) => fetchApi<ImportJob>(`/import/jobs/${id}`),

  getAIQueries: (page = 1) => fetchApi<AIQuery[]>(`/admin/ai/queries?page=${page}`),
  getAIEvents: (queryId: number) => fetchApi<AIEvent[]>(`/admin/ai/queries/${queryId}/events`),
  getAIStats: () => fetchApi<Record<string, number>>("/admin/ai/stats"),

  getEvalMetrics: () => fetchApi<Record<string, number>>("/eval/metrics"),
  getRecentRetrievals: () => fetchApi<Record<string, unknown>[]>("/eval/recent-retrievals"),
};
