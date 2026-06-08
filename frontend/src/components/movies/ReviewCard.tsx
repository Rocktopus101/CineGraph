import Link from "next/link";
import type { ReviewItem } from "@/lib/types";
import { RatingStars } from "./RatingStars";
import { Card, CardContent } from "@/components/ui/card";

export function ReviewCard({ review }: { review: ReviewItem }) {
  return (
    <Card>
      <CardContent className="p-4">
        <Link href={`/movies/${review.movie.id}`} className="font-medium hover:text-primary">
          {review.movie.title} {review.movie.year && `(${review.movie.year})`}
        </Link>
        {review.rating != null && <div className="mt-1"><RatingStars rating={review.rating} size="sm" /></div>}
        {review.review_text && (
          <p className="mt-2 text-sm text-muted-foreground line-clamp-4">{review.review_text}</p>
        )}
        {review.watched_date && (
          <p className="mt-2 text-xs text-muted-foreground">Watched {review.watched_date}</p>
        )}
      </CardContent>
    </Card>
  );
}
