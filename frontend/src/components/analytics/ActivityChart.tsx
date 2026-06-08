"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  data: { month: string; count: number }[];
}

export function ActivityChart({ data }: Props) {
  if (!data.length) return <p className="text-sm text-muted-foreground">No activity data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data}>
        <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#9ab" />
        <YAxis tick={{ fontSize: 11 }} stroke="#9ab" />
        <Tooltip
          contentStyle={{ background: "#1c2228", border: "1px solid #2c3440", borderRadius: 8 }}
        />
        <Bar dataKey="count" fill="#00c853" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
