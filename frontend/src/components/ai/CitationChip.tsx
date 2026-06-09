import Link from "next/link";
import type { Citation } from "@/lib/types";
import { Star } from "lucide-react";

function shortChipTitle(title: string): string {
  const match = title.match(/^(.+?)\s*\(\d{4}\)\s*:/);
  if (match) return match[1].trim();
  return title.length > 48 ? `${title.slice(0, 45).trim()}…` : title;
}

export function CitationChip({ citation }: { citation: Citation }) {
  const isRecommendation = citation.rating == null && !citation.watched_date;
  const label = isRecommendation ? shortChipTitle(citation.title) : citation.title;

  return (
    <Link
      href={`/movies/${citation.movie_id}`}
      className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs hover:bg-primary/20 transition-colors"
    >
      {isRecommendation && (
        <span className="text-[10px] uppercase tracking-wide text-primary/80">Suggested</span>
      )}
      <span className="font-medium line-clamp-1 max-w-[14rem]">{label}</span>
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
