"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { isDevMode } from "@/lib/firebase";

export default function HomePage() {
  const { user, loading } = useAuth();
  const skipOnboarding = isDevMode && process.env.NEXT_PUBLIC_DEV_MODE === "true";

  const { data: history, isLoading } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.getHistory({ limit: "12" }),
    enabled: !!user?.has_completed_import || skipOnboarding,
  });

  if (loading) {
    return <div className="space-y-4">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-48" />)}</div>;
  }

  if (!user?.has_completed_import && !skipOnboarding) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <h1 className="text-3xl font-bold mb-4">Welcome to CineGraph</h1>
        <p className="text-muted-foreground mb-8 max-w-md">
          Import your Letterboxd data to unlock personalized recommendations and taste analytics.
        </p>
        <Link href="/onboarding/import">
          <Button size="lg">Get Started</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-lg bg-gradient-to-r from-primary/10 to-transparent p-8">
        <h1 className="text-3xl font-bold mb-2">Your cinematic universe</h1>
        <p className="text-muted-foreground mb-4">Explore your watch history and get AI-powered recommendations.</p>
        <Link href="/recommendations">
          <Button>Ask AI for recommendations</Button>
        </Link>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Recent Watches</h2>
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="aspect-[2/3]" />)}
          </div>
        ) : history && history.length > 0 ? (
          <MovieGrid
            movies={history.map((h) => h.movie)}
            ratings={Object.fromEntries(history.filter((h) => h.rating).map((h) => [h.movie.id, h.rating!]))}
          />
        ) : (
          <p className="text-muted-foreground">No watch history yet.</p>
        )}
      </section>
    </div>
  );
}
