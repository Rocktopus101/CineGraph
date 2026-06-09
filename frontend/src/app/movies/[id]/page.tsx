"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PosterHero } from "@/components/movies/PosterHero";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { letterboxdUrl } from "@/lib/utils";
import { ExternalLink } from "lucide-react";

export default function MovieDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const movieId = parseInt(id);
  const qc = useQueryClient();

  const { data: movie, isLoading } = useQuery({
    queryKey: ["movie", movieId],
    queryFn: () => api.getMovie(movieId),
  });

  const { data: similar } = useQuery({
    queryKey: ["similar", movieId],
    queryFn: () => api.getSimilar(movieId),
    enabled: !!movie,
  });

  const watchlistMutation = useMutation({
    mutationFn: () => api.addToWatchlist(movieId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["movie", movieId] }),
  });

  if (isLoading) return <Skeleton className="h-96" />;
  if (!movie) return <p>Movie not found</p>;

  return (
    <div className="space-y-8">
      <PosterHero movie={movie} />
      <div className="flex flex-wrap gap-3">
        {!movie.in_watchlist && (
          <Button onClick={() => watchlistMutation.mutate()} disabled={watchlistMutation.isPending}>
            Add to Watchlist
          </Button>
        )}
        {movie.in_watchlist && <Button variant="outline" disabled>On Watchlist</Button>}
        <Button variant="outline" asChild>
          <a href={letterboxdUrl(movie)} target="_blank" rel="noopener noreferrer">
            View on Letterboxd
            <ExternalLink className="ml-2 h-4 w-4" />
          </a>
        </Button>
      </div>
      {movie.user_review && (
        <div className="rounded-lg border border-border p-4">
          <h3 className="font-medium mb-2">Your Review</h3>
          <p className="text-sm text-muted-foreground">{movie.user_review}</p>
        </div>
      )}
      {similar && similar.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Similar Films</h2>
          <MovieGrid movies={similar} />
        </section>
      )}
    </div>
  );
}
