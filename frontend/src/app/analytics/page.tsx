"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { TasteInsightCard } from "@/components/analytics/TasteInsightCard";
import { ActivityChart } from "@/components/analytics/ActivityChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { isDevMode } from "@/lib/firebase";

export default function AnalyticsPage() {
  const { user } = useAuth();
  const skipOnboarding = isDevMode && process.env.NEXT_PUBLIC_DEV_MODE === "true";

  const { data: taste } = useQuery({
    queryKey: ["taste"],
    queryFn: () => api.getTaste(),
    enabled: !!user?.has_completed_import || skipOnboarding,
  });

  const { data: analytics } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => api.getAnalytics(),
    enabled: !!user?.has_completed_import || skipOnboarding,
  });

  if (!user?.has_completed_import && !skipOnboarding) {
    return (
      <div className="text-center py-20">
        <h1 className="text-2xl font-bold mb-4">Analytics</h1>
        <p className="text-muted-foreground mb-6">Import your Letterboxd data to see taste analytics.</p>
        <Link href="/onboarding/import"><Button>Import Data</Button></Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Taste Analytics</h1>
      {taste && <TasteInsightCard summary={taste.summary_text} />}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-lg">Top Genres</CardTitle></CardHeader>
          <CardContent>
            {analytics?.genres?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={analytics.genres} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ab" />
                  <YAxis dataKey="genre" type="category" width={80} tick={{ fontSize: 11 }} stroke="#9ab" />
                  <Tooltip contentStyle={{ background: "#1c2228", border: "1px solid #2c3440" }} />
                  <Bar dataKey="score" fill="#00c853" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground">No genre data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Viewing Activity</CardTitle></CardHeader>
          <CardContent>
            <ActivityChart data={analytics?.monthly_activity || []} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Decade Preferences</CardTitle></CardHeader>
          <CardContent>
            {analytics?.decades?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={analytics.decades}>
                  <XAxis dataKey="decade" tick={{ fontSize: 11 }} stroke="#9ab" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#9ab" />
                  <Tooltip contentStyle={{ background: "#1c2228", border: "1px solid #2c3440" }} />
                  <Bar dataKey="count" fill="#00c853" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground">No decade data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-lg">Top Directors</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {analytics?.top_directors?.slice(0, 8).map((d) => (
                <li key={d.director} className="flex justify-between text-sm">
                  <span>{d.director}</span>
                  <span className="text-primary">{d.score.toFixed(1)}</span>
                </li>
              )) || <p className="text-sm text-muted-foreground">No director data</p>}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
