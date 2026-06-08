import { CheckCircle2, Loader2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGES = [
  { key: "pending", label: "Starting import" },
  { key: "parsing", label: "Parsing your history" },
  { key: "enriching", label: "Enriching movies (may take a few minutes)" },
  { key: "embedding", label: "Embedding movie catalog" },
  { key: "embedding_history", label: "Indexing your watch history" },
  { key: "profiling", label: "Building taste profile & lists" },
  { key: "complete", label: "All set!" },
];

const STAGE_ORDER = STAGES.map((s) => s.key);

function resolveStageIndex(status: string, stage: string): number {
  const keys = [stage, status];
  for (const key of keys) {
    const idx = STAGE_ORDER.indexOf(key);
    if (idx >= 0) return idx;
  }
  if (status === "embedding" || stage === "embedding") {
    return STAGE_ORDER.indexOf("embedding");
  }
  return 0;
}

interface Props {
  status: string;
  stats?: Record<string, unknown> | null;
}

export function ImportProgressStepper({ status, stats }: Props) {
  const progress = (stats?.progress as number) || (status === "pending" ? 5 : 0);
  const stage = (stats?.stage as string) || status;
  const stageIndex = resolveStageIndex(status, stage);

  return (
    <div className="space-y-6">
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">{progress}% complete</p>
      <div className="space-y-3">
        {STAGES.map((s, i) => {
          const done = i < stageIndex || status === "complete";
          const active = i === stageIndex && status !== "complete" && status !== "failed";
          return (
            <div key={s.key} className="flex items-center gap-3">
              {done ? (
                <CheckCircle2 className="h-5 w-5 text-primary" />
              ) : active ? (
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              ) : (
                <Circle className="h-5 w-5 text-muted-foreground" />
              )}
              <span className={cn("text-sm", active && "text-primary font-medium", done && "text-foreground")}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
      {stats?.films_parsed != null && status !== "complete" && !stage.startsWith("embedding") && (
        <p className="text-xs text-muted-foreground">
          Processed {String(stats.films_parsed)}
          {stats.films_total != null ? ` / ${String(stats.films_total)}` : ""} films
        </p>
      )}
      {stage === "profiling" && stats?.profiling_step != null && status !== "complete" && (
        <p className="text-xs text-muted-foreground">
          {stats.profiling_step === "lists"
            ? "Generating taste lists…"
            : "Computing taste statistics…"}
        </p>
      )}
      {(stage === "embedding" || stage === "embedding_history") && status !== "complete" && (
        <p className="text-xs text-muted-foreground">
          {stage === "embedding_history" && stats?.user_skipped_api
            ? "Skipping review embeddings to avoid API limits — wrapping up…"
            : [
                stage === "embedding" && stats?.movies_embedded != null
                  ? `Movies ${String(stats.movies_embedded)}${stats.movies_total != null ? ` / ${String(stats.movies_total)}` : ""}`
                  : null,
                stage === "embedding_history" && stats?.user_embedded != null
                  ? `History ${String(stats.user_embedded)}${stats.user_total != null ? ` / ${String(stats.user_total)}` : ""}`
                  : null,
                "Batched for free-tier limits — may take several minutes",
              ]
                .filter(Boolean)
                .join(" · ")}
        </p>
      )}
      {status === "failed" && (
        <p className="text-sm text-red-400">Import failed. Please try again or use sample data.</p>
      )}
    </div>
  );
}
