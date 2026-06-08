"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { ImportJob } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { LetterboxdExportGuide } from "@/components/import/LetterboxdExportGuide";
import { LetterboxdUploadDropzone } from "@/components/import/LetterboxdUploadDropzone";
import { ImportProgressStepper } from "@/components/import/ImportProgressStepper";
import { DemoDataButton } from "@/components/import/DemoDataButton";
import { Button } from "@/components/ui/button";

const STEPS = [
  { num: 1, title: "Export your data" },
  { num: 2, title: "Upload your export" },
  { num: 3, title: "Processing" },
];

export default function OnboardingImportPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [step, setStep] = useState(1);
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
          setTimeout(() => router.push("/analytics"), 1500);
        }
        if (updated.status === "failed" || updated.status === "cancelled") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [job, router]);

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Import your Letterboxd data</h1>
        <p className="text-muted-foreground">This unlocks personalized recommendations and taste analytics.</p>
      </div>

      <div className="flex gap-2">
        {STEPS.map((s) => (
          <div
            key={s.num}
            className={`flex-1 rounded-md px-3 py-2 text-center text-xs ${
              step >= s.num ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
            }`}
          >
            {s.title}
          </div>
        ))}
      </div>

      {step === 1 && (
        <LetterboxdExportGuide
          onConfirmDownload={() => {
            setExportConfirmed(true);
            setStep(2);
          }}
          confirmed={exportConfirmed}
        />
      )}

      {step === 2 && !job && (
        <div className="space-y-4">
          <LetterboxdUploadDropzone
            disabled={!exportConfirmed}
            onUpload={async (file) => {
              const newJob = await api.importLetterboxd(file);
              setJob(newJob);
              setStep(3);
            }}
          />
          <DemoDataButton
            onLoad={async () => {
              const newJob = await api.loadDemoData();
              setJob(newJob);
              setStep(3);
              await refreshUser();
              setTimeout(() => router.push("/analytics"), 1500);
            }}
          />
        </div>
      )}

      {step === 3 && job && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">
            {job.stats_json?.source === "demo" ? "Loading sample data..." : "Processing your data..."}
          </h2>
          <ImportProgressStepper status={job.status} stats={job.stats_json} />
          {job.status === "complete" && (
            <p className="text-primary text-sm">
              {job.stats_json?.source === "demo"
                ? "Sample data ready! Redirecting..."
                : "All set! Redirecting to analytics..."}
            </p>
          )}
          {job.status !== "complete" && job.status !== "failed" && job.status !== "cancelled" && (
            <div className="space-y-3 pt-2">
              <p className="text-xs text-muted-foreground">
                Taking too long? Cancel and use sample data instead.
              </p>
              <div className="flex flex-wrap gap-2">
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
              </div>
              <DemoDataButton
                onLoad={async () => {
                  const newJob = await api.loadDemoData();
                  setJob(newJob);
                  setStep(3);
                  await refreshUser();
                  setTimeout(() => router.push("/analytics"), 1500);
                }}
              />
            </div>
          )}
          {(job.error || job.status === "cancelled") && job.status !== "complete" && (
            <p className="text-red-400 text-sm">{job.error || "Import cancelled."}</p>
          )}
        </div>
      )}
    </div>
  );
}
