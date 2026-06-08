"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ReviewCard } from "@/components/movies/ReviewCard";
import { Skeleton } from "@/components/ui/skeleton";

export default function ReviewsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.getReviews(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Your Reviews</h1>
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
      )}
      {data && data.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((r) => <ReviewCard key={r.id} review={r} />)}
        </div>
      ) : (
        !isLoading && <p className="text-muted-foreground">No reviews imported yet.</p>
      )}
    </div>
  );
}
