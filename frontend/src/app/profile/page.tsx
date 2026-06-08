"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TasteInsightCard } from "@/components/analytics/TasteInsightCard";

export default function ProfilePage() {
  const { user } = useAuth();
  const { data: taste } = useQuery({
    queryKey: ["taste"],
    queryFn: () => api.getTaste(),
    enabled: !!user,
  });

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Profile</h1>
      <Card>
        <CardHeader>
          <CardTitle>{user?.display_name || "User"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p><span className="text-muted-foreground">Email:</span> {user?.email}</p>
          {user?.letterboxd_username && (
            <p><span className="text-muted-foreground">Letterboxd:</span> @{user.letterboxd_username}</p>
          )}
          <p>
            <span className="text-muted-foreground">Import status:</span>{" "}
            {user?.has_completed_import ? "Complete" : "Pending"}
          </p>
        </CardContent>
      </Card>
      {taste && <TasteInsightCard summary={taste.summary_text} />}
    </div>
  );
}
