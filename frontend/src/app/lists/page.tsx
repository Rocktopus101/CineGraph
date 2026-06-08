"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function ListsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["lists"],
    queryFn: () => api.getLists(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Taste Lists</h1>
      <p className="text-sm text-muted-foreground">Auto-generated lists based on your viewing patterns.</p>
      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.map((list) => (
          <Link key={list.id} href={`/lists/${list.id}`}>
            <Card className="hover:border-primary/50 transition-colors h-full">
              <CardHeader>
                <CardTitle className="text-lg">{list.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{list.description}</p>
                <p className="text-xs text-primary mt-2">{list.item_count} films</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      {!isLoading && data?.length === 0 && (
        <p className="text-muted-foreground">No lists generated yet. Complete an import first.</p>
      )}
    </div>
  );
}
