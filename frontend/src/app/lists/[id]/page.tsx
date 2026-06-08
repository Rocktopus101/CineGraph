"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MovieGrid } from "@/components/movies/MovieGrid";
import { Skeleton } from "@/components/ui/skeleton";

export default function ListDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const listId = parseInt(id);

  const { data, isLoading } = useQuery({
    queryKey: ["list", listId],
    queryFn: () => api.getList(listId),
  });

  if (isLoading) return <Skeleton className="h-96" />;
  if (!data) return <p>List not found</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{data.name}</h1>
        {data.description && <p className="text-muted-foreground mt-1">{data.description}</p>}
      </div>
      <MovieGrid movies={data.items} />
    </div>
  );
}
