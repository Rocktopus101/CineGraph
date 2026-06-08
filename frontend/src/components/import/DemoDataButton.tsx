"use client";

import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  onLoad: () => Promise<void>;
  disabled?: boolean;
}

export function DemoDataButton({ onLoad, disabled }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    try {
      await onLoad();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sample data");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-3">
      <div className="flex items-start gap-3">
        <Sparkles className="h-5 w-5 text-primary mt-0.5 shrink-0" />
        <div className="space-y-1">
          <p className="text-sm font-medium">Explore with sample data</p>
          <p className="text-xs text-muted-foreground">
            Upload stuck or hitting API limits? This cancels any running import and loads 20
            prebaked films instantly — no embedding API calls.
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        onClick={handleClick}
        disabled={disabled || loading}
        className="w-full sm:w-auto"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            Loading sample data...
          </>
        ) : (
          "Use sample data"
        )}
      </Button>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
