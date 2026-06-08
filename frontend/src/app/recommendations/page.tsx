"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { AIChatPanel } from "@/components/ai/AIChatPanel";
import { Button } from "@/components/ui/button";
import { isDevMode } from "@/lib/firebase";

export default function RecommendationsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const skipOnboarding = isDevMode && process.env.NEXT_PUBLIC_DEV_MODE === "true";

  useEffect(() => {
    if (!isDevMode && !loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (!user?.has_completed_import && !skipOnboarding) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold mb-4">AI Recommendations</h1>
        <p className="text-muted-foreground mb-6">Import your Letterboxd data to get personalized recommendations.</p>
        <Link href="/onboarding/import"><Button>Import Data</Button></Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">AI Recommendations</h1>
      <p className="text-sm text-muted-foreground mb-4">
        Grounded in your actual viewing history with citation-backed suggestions.
      </p>
      <AIChatPanel onSend={async (msg) => {
        const res = await api.chat(msg);
        return { response: res.response, citations: res.citations };
      }} />
    </div>
  );
}
