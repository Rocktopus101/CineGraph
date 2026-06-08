"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { ImportJob } from "@/lib/types";
import { LetterboxdExportGuide } from "@/components/import/LetterboxdExportGuide";
import { LetterboxdUploadDropzone } from "@/components/import/LetterboxdUploadDropzone";
import { ImportProgressStepper } from "@/components/import/ImportProgressStepper";
import { DemoDataButton } from "@/components/import/DemoDataButton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [exportConfirmed, setExportConfirmed] = useState(false);
  const [job, setJob] = useState<ImportJob | null>(null);

  useEffect(() => {
    if (!job || job.status === "complete" || job.status === "failed" || job.status === "cancelled") {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const updated = await api.getImportJob(job.id);
        setJob(updated);
        if (updated.status === "complete") {
          clearInterval(interval);
          await refreshUser();
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [job, refreshUser]);

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-1">
          <p>{user?.display_name || user?.email}</p>
          {user?.letterboxd_username && (
            <p className="text-muted-foreground">@{user.letterboxd_username}</p>
          )}
        </CardContent>
      </Card>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Re-import Letterboxd Data</h2>
        <LetterboxdExportGuide
          onConfirmDownload={() => setExportConfirmed(true)}
          confirmed={exportConfirmed}
        />
        {exportConfirmed && !job && (
          <div className="space-y-4">
            <LetterboxdUploadDropzone
              onUpload={async (file) => {
                const newJob = await api.importLetterboxd(file);
                setJob(newJob);
              }}
            />
            <DemoDataButton
              onLoad={async () => {
                const newJob = await api.loadDemoData();
                setJob(newJob);
                await refreshUser();
              }}
            />
          </div>
        )}
        {job && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">Import progress</h3>
            <ImportProgressStepper status={job.status} stats={job.stats_json} />
            {job.status === "complete" && (
              <p className="text-sm text-primary">
                Import complete. Your watch history and recommendations are updated.
              </p>
            )}
            {job.status !== "complete" &&
              job.status !== "failed" &&
              job.status !== "cancelled" && (
                <div className="space-y-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      const updated = await api.cancelImportJob(job.id);
                      setJob(updated);
                    }}
                  >
                    Cancel import
                  </Button>
                  <DemoDataButton
                    onLoad={async () => {
                      const newJob = await api.loadDemoData();
                      setJob(newJob);
                      await refreshUser();
                    }}
                  />
                </div>
              )}
            {(job.error || job.status === "cancelled") && job.status !== "complete" && (
              <p className="text-sm text-red-400">{job.error || "Import cancelled."}</p>
            )}
            {(job.status === "complete" || job.status === "failed" || job.status === "cancelled") && (
              <button
                type="button"
                className="text-sm text-primary underline"
                onClick={() => setJob(null)}
              >
                Upload another export
              </button>
            )}
          </div>
        )}
      </section>

      <Card>
        <CardHeader><CardTitle>API Status</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Backend: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
        </CardContent>
      </Card>
    </div>
  );
}

