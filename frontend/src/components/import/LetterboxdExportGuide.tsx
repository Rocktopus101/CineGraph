"use client";

import { useState } from "react";
import { ExternalLink, CheckCircle2, Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const EXPORT_URL = "https://letterboxd.com/user/exportdata/";

interface Props {
  onConfirmDownload?: () => void;
  confirmed?: boolean;
}

export function LetterboxdExportGuide({ onConfirmDownload, confirmed = false }: Props) {
  const [checked, setChecked] = useState(confirmed);

  const steps = [
    "Open the Letterboxd export page (link below)",
    'Click the "Export Your Data" button',
    "Wait for Letterboxd to prepare your archive (may take a few minutes)",
    "Download the ZIP file (named like letterboxd-username-timestamp-utc.zip)",
  ];

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="text-xl">Export from Letterboxd</CardTitle>
        <p className="text-sm text-muted-foreground">
          You must be logged into your Letterboxd account for the export to contain your data.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <ol className="space-y-3">
          {steps.map((step, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>

        <a href={EXPORT_URL} target="_blank" rel="noopener noreferrer">
          <Button className="w-full sm:w-auto">
            <ExternalLink className="mr-2 h-4 w-4" />
            Open Letterboxd Export Page
          </Button>
        </a>

        <div className="rounded-md border border-border bg-muted/50 p-4 text-sm text-muted-foreground">
          <p className="font-medium text-foreground mb-1">What&apos;s in the ZIP?</p>
          <p>Watched films, ratings, reviews, diary entries, watchlist, and profile data.</p>
        </div>

        <button
          type="button"
          onClick={() => {
            setChecked(true);
            onConfirmDownload?.();
          }}
          className="flex items-center gap-2 text-sm hover:text-primary transition-colors"
        >
          {checked ? (
            <CheckCircle2 className="h-5 w-5 text-primary" />
          ) : (
            <Circle className="h-5 w-5 text-muted-foreground" />
          )}
          I&apos;ve downloaded my ZIP file
        </button>
      </CardContent>
    </Card>
  );
}

export function isExportConfirmed() {
  return true;
}
