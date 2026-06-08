import { CheckCircle2, Loader2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGES = [
  { key: "pending", label: "Starting import", step: 2 },
  { key: "parsing", label: "Parsing your history", step: 3 },
  { key: "enriching", label: "Enriching movies (may take a few minutes)", step: 4 },
  { key: "embedding", label: "Building your taste map", step: 5 },
  { key: "profiling", label: "Building taste profile & lists", step: 5 },
  { key: "complete", label: "All set!", step: 6 },
];

interface Props {
  status: string;
  stats?: Record<string, unknown> | null;
}

export function ImportProgressStepper({ status, stats }: Props) {
  const progress = (stats?.progress as number) || (status === "pending" ? 5 : 0);
  const stage = (stats?.stage as string) || status;

  const stageIndex = STAGES.findIndex((s) => s.key === stage || s.key === status);

  return (
    <div className="space-y-6">
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
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
      {stats?.films_parsed != null && status !== "complete" && stage !== "embedding" && (
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
      {stage === "embedding" && status !== "complete" && (
        <p className="text-xs text-muted-foreground">
          Embedding
          {stats?.movies_embedded != null
            ? ` movies ${String(stats.movies_embedded)}${stats.movies_total != null ? ` / ${String(stats.movies_total)}` : ""}`
            : ""}
          {stats?.user_embedded != null
            ? ` · history ${String(stats.user_embedded)}${stats.user_total != null ? ` / ${String(stats.user_total)}` : ""}`
            : ""}
          {" "}(batched for free-tier limits — may take several minutes)
        </p>
      )}
      {status === "failed" && (
        <p className="text-sm text-red-400">Import failed. Please try again.</p>
      )}
    </div>
  );
}
