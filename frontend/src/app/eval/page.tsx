"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function EvalPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ["eval-metrics"],
    queryFn: () => api.getEvalMetrics(),
  });

  const { data: retrievals } = useQuery({
    queryKey: ["eval-retrievals"],
    queryFn: () => api.getRecentRetrievals(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Retrieval Evaluation</h1>

      {isLoading && <Skeleton className="h-32" />}

      {metrics && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Object.entries(metrics).map(([k, v]) => (
            <Card key={k}>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">{k.replace(/_/g, " ")}</p>
                <p className="text-2xl font-bold text-primary">{v}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader><CardTitle className="text-lg">Recent Retrievals</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {retrievals?.map((r, i) => (
            <div key={i} className="rounded-md border border-border p-3 text-sm">
              <p className="text-xs text-muted-foreground">Query #{String(r.query_id)} — {String(r.latency_ms)}ms</p>
              <div className="mt-2 space-y-1">
                {(r.docs as { movie_id?: number; score?: number; type?: string }[] || []).map((d, j) => (
                  <p key={j} className="text-xs">
                    Movie {d.movie_id} — score {d.score?.toFixed(3)} ({d.type})
                  </p>
                ))}
              </div>
            </div>
          )) || <p className="text-sm text-muted-foreground">No retrieval data yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
