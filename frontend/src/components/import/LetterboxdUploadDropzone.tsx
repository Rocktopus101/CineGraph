"use client";

import { useCallback, useState } from "react";
import { Upload, FileArchive } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const MAX_SIZE_MB = 50;

interface Props {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export function LetterboxdUploadDropzone({ onUpload, disabled }: Props) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const validate = (f: File): string | null => {
    if (!f.name.endsWith(".zip")) return "File must be a .zip archive";
    if (f.size > MAX_SIZE_MB * 1024 * 1024) return `File exceeds ${MAX_SIZE_MB}MB limit`;
    return null;
  };

  const handleFile = (f: File) => {
    const err = validate(f);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(30);
    try {
      await onUpload(file);
      setProgress(100);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-border",
          disabled && "opacity-50 pointer-events-none"
        )}
      >
        <Upload className="h-10 w-10 text-muted-foreground mb-4" />
        <p className="text-sm text-muted-foreground mb-2">Drag and drop your Letterboxd ZIP here</p>
        <label>
          <input
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <Button variant="outline" asChild>
            <span>Choose file</span>
          </Button>
        </label>
      </div>

      {file && (
        <div className="flex items-center gap-3 rounded-md bg-muted p-3">
          <FileArchive className="h-5 w-5 text-primary" />
          <span className="text-sm flex-1 truncate">{file.name}</span>
          <Button onClick={handleUpload} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </Button>
        </div>
      )}

      {uploading && <Progress value={progress} />}
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
