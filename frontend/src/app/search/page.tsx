"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Skeleton } from "@/components/ui/skeleton";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["search", search],
    queryFn: () => api.searchMovies(search),
    enabled: search.length > 0,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Search Movies</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(query);
        }}
        className="flex gap-2"
      >
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by title..."
          className="max-w-md"
        />
      </form>
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="aspect-[2/3]" />)}
        </div>
      )}
      {data && <MovieGrid movies={data} />}
      {search && !isLoading && data?.length === 0 && (
        <p className="text-muted-foreground">No results for &quot;{search}&quot;</p>
      )}
    </div>
  );
}
