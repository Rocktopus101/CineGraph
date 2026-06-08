"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminAIPage() {
  const [selectedQuery, setSelectedQuery] = useState<number | null>(null);

  const { data: queries, isLoading } = useQuery({
    queryKey: ["admin-queries"],
    queryFn: () => api.getAIQueries(),
  });

  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => api.getAIStats(),
  });

  const { data: events } = useQuery({
    queryKey: ["admin-events", selectedQuery],
    queryFn: () => api.getAIEvents(selectedQuery!),
    enabled: !!selectedQuery,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">AI Activity Log</h1>

      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          {Object.entries(stats).map(([k, v]) => (
            <Card key={k}>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{k.replace(/_/g, " ")}</p>
                <p className="text-2xl font-bold text-primary">{typeof v === "number" ? v.toLocaleString() : v}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-lg">Recent Queries</CardTitle></CardHeader>
          <CardContent className="space-y-2 max-h-96 overflow-y-auto">
            {isLoading && <Skeleton className="h-20" />}
            {queries?.map((q) => (
              <button
                key={q.id}
                onClick={() => setSelectedQuery(q.id)}
                className={`w-full text-left rounded-md p-3 text-sm hover:bg-muted transition-colors ${
                  selectedQuery === q.id ? "bg-muted border border-primary/30" : ""
                }`}
              >
                <p className="font-medium truncate">{q.query_text}</p>
                <p className="text-xs text-muted-foreground">{new Date(q.created_at).toLocaleString()}</p>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Event Timeline</CardTitle></CardHeader>
          <CardContent className="space-y-3 max-h-96 overflow-y-auto">
            {!selectedQuery && <p className="text-sm text-muted-foreground">Select a query to view events</p>}
            {events?.map((e) => (
              <div key={e.id} className="rounded-md border border-border p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium text-primary">{e.event_type}</span>
                  {e.latency_ms != null && <span className="text-xs text-muted-foreground">{e.latency_ms}ms</span>}
                </div>
                {e.tokens_in != null && (
                  <p className="text-xs text-muted-foreground mt-1">
                    tokens: {e.tokens_in} in / {e.tokens_out} out
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
