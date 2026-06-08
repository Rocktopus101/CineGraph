"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { isDevMode } from "@/lib/firebase";

export default function WatchlistPage() {
  const { user } = useAuth();
  const skipOnboarding = isDevMode && process.env.NEXT_PUBLIC_DEV_MODE === "true";

  const { data, isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api.getWatchlist(),
    enabled: !!user?.has_completed_import || skipOnboarding,
  });

  if (!user?.has_completed_import && !skipOnboarding) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold mb-4">Watchlist</h1>
        <p className="text-muted-foreground mb-6">Import your Letterboxd data to see your watchlist.</p>
        <Link href="/onboarding/import"><Button>Import Data</Button></Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Watchlist</h1>
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="aspect-[2/3]" />)}
        </div>
      )}
      {data && data.length > 0 ? (
        <MovieGrid movies={data.map((w) => w.movie)} />
      ) : (
        !isLoading && <p className="text-muted-foreground">Your watchlist is empty.</p>
      )}
    </div>
  );
}
