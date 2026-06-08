export interface User {
  id: number;
  firebase_uid: string;
  email: string | null;
  display_name: string | null;
  letterboxd_username: string | null;
  is_admin: boolean;
  has_completed_import: boolean;
  created_at: string;
}

export interface Movie {
  id: number;
  tmdb_id: number | null;
  title: string;
  year: number | null;
  poster_path: string | null;
  vote_average: number | null;
  overview?: string | null;
}

export interface MovieDetail extends Movie {
  original_title: string | null;
  runtime: number | null;
  backdrop_path: string | null;
  release_date: string | null;
  letterboxd_uri: string | null;
  metadata_json: Record<string, unknown> | null;
  user_rating: number | null;
  user_review: string | null;
  watched_date: string | null;
  in_watchlist: boolean;
}

export interface HistoryItem {
  id: number;
  movie: Movie;
  watched_date: string | null;
  rating: number | null;
  review_text: string | null;
  source: string;
}

export interface ReviewItem {
  id: number;
  movie: Movie;
  review_text: string | null;
  rating: number | null;
  watched_date: string | null;
}

export interface WatchlistItem {
  id: number;
  movie: Movie;
  added_at: string;
}

export interface ListSummary {
  id: number;
  name: string;
  list_type: string;
  description: string | null;
  item_count: number;
}

export interface ListDetail {
  id: number;
  name: string;
  list_type: string;
  description: string | null;
  items: Movie[];
}

export interface TasteProfile {
  summary_text: string | null;
  insights_json: Record<string, unknown> | null;
  computed_at: string | null;
}

export interface Analytics {
  genres: { genre: string; score: number }[];
  decades: { decade: string; count: number }[];
  monthly_activity: { month: string; count: number }[];
  top_directors: { director: string; score: number }[];
  average_rating_by_genre: { genre: string; avg_rating: number }[];
  avoided_genres: { genre: string; count: number }[];
}

export interface Citation {
  movie_id: number;
  title: string;
  rating: number | null;
  watched_date: string | null;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  query_id: number | null;
}

export interface ImportJob {
  id: number;
  status: string;
  file_hash: string | null;
  started_at: string;
  completed_at: string | null;
  stats_json: Record<string, unknown> | null;
  error: string | null;
}

export interface AIQuery {
  id: number;
  user_id: number;
  query_text: string;
  response_text: string | null;
  created_at: string;
}

export interface AIEvent {
  id: number;
  query_id: number;
  event_type: string;
  payload_json: Record<string, unknown> | null;
  latency_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
}
