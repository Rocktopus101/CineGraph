import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function posterUrl(path: string | null | undefined, size = "w342"): string | null {
  if (!path) return null;
  return `https://image.tmdb.org/t/p/${size}${path}`;
}

export function cleanMovieTitle(title: string): string {
  const match = title.match(/^(.+?)\s*\((\d{4})\)\s*:/);
  if (match) return `${match[1].trim()} (${match[2]})`;
  return title.length > 100 ? `${title.slice(0, 97).trim()}…` : title;
}

export function letterboxdUrl(movie: {
  title: string;
  year?: number | null;
  letterboxd_uri?: string | null;
}): string {
  if (movie.letterboxd_uri) {
    const uri = movie.letterboxd_uri.trim();
    if (uri.startsWith("http://") || uri.startsWith("https://")) return uri;
    return `https://${uri}`;
  }
  const query = movie.year ? `${movie.title} ${movie.year}` : movie.title;
  return `https://letterboxd.com/search/${encodeURIComponent(query)}/`;
}
