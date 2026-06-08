import Link from "next/link";
import type { Citation } from "@/lib/types";
import { Star } from "lucide-react";

export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <Link
      href={`/movies/${citation.movie_id}`}
      className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs hover:bg-primary/20 transition-colors"
    >
      <span className="font-medium">{citation.title}</span>
      {citation.rating != null && (
        <span className="flex items-center gap-0.5 text-primary">
          <Star className="h-3 w-3 fill-primary" />
          {citation.rating}
        </span>
      )}
      {citation.watched_date && (
        <span className="text-muted-foreground">{citation.watched_date}</span>
      )}
    </Link>
  );
}
