import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TasteInsightCard({ summary }: { summary: string | null }) {
  if (!summary) return null;
  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="text-lg">Your Taste Profile</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground">{summary}</p>
      </CardContent>
    </Card>
  );
}
