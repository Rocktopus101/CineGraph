import Image from "next/image";
import Link from "next/link";
import { posterUrl } from "@/lib/utils";
import type { Movie } from "@/lib/types";
import { RatingStars } from "./RatingStars";

interface MovieCardProps {
  movie: Movie;
  rating?: number | null;
}

export function MovieCard({ movie, rating }: MovieCardProps) {
  const poster = posterUrl(movie.poster_path);
  return (
    <Link href={`/movies/${movie.id}`} className="group block">
      <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-muted">
        {poster ? (
          <Image
            src={poster}
            alt={movie.title}
            fill
            className="object-cover transition-transform group-hover:scale-105"
            sizes="200px"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm p-2 text-center">
            {movie.title}
          </div>
        )}
      </div>
      <div className="mt-2">
        <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
          {movie.title}
        </p>
        {movie.year && <p className="text-xs text-muted-foreground">{movie.year}</p>}
        {rating != null && <RatingStars rating={rating} size="sm" />}
      </div>
    </Link>
  );
}
