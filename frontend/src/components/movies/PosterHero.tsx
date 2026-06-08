import Image from "next/image";
import { posterUrl } from "@/lib/utils";
import type { MovieDetail } from "@/lib/types";
import { RatingStars } from "./RatingStars";

export function PosterHero({ movie }: { movie: MovieDetail }) {
  const backdrop = movie.backdrop_path
    ? `https://image.tmdb.org/t/p/w1280${movie.backdrop_path}`
    : null;
  const poster = posterUrl(movie.poster_path, "w500");

  return (
    <div className="relative overflow-hidden rounded-lg">
      {backdrop && (
        <div className="absolute inset-0">
          <Image src={backdrop} alt="" fill className="object-cover opacity-30 blur-sm" priority />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent" />
        </div>
      )}
      <div className="relative flex flex-col gap-6 p-6 md:flex-row md:p-10">
        <div className="relative mx-auto h-72 w-48 shrink-0 overflow-hidden rounded-md shadow-2xl md:mx-0">
          {poster ? (
            <Image src={poster} alt={movie.title} fill className="object-cover" priority />
          ) : (
            <div className="flex h-full items-center justify-center bg-muted p-4 text-center">{movie.title}</div>
          )}
        </div>
        <div className="flex flex-col justify-end">
          <h1 className="text-3xl font-bold md:text-4xl">{movie.title}</h1>
          {movie.year && <p className="mt-1 text-muted-foreground">{movie.year}</p>}
          {movie.user_rating != null && (
            <div className="mt-3">
              <p className="text-xs text-muted-foreground mb-1">Your rating</p>
              <RatingStars rating={movie.user_rating} />
            </div>
          )}
          {movie.overview && (
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground">{movie.overview}</p>
          )}
          {Array.isArray(movie.metadata_json?.genres) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {(movie.metadata_json!.genres as string[]).map((g) => (
                <span key={g} className="rounded-full bg-muted px-3 py-1 text-xs">{g}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
