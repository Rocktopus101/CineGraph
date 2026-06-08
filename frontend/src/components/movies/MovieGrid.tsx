import type { Movie } from "@/lib/types";
import { MovieCard } from "./MovieCard";

interface MovieGridProps {
  movies: Movie[];
  ratings?: Record<number, number>;
}

export function MovieGrid({ movies, ratings }: MovieGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {movies.map((m) => (
        <MovieCard key={m.id} movie={m} rating={ratings?.[m.id]} />
      ))}
    </div>
  );
}
