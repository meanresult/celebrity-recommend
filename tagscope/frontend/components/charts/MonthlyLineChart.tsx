"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Props {
  data: { month: string; tagger_count: number }[];
}

export function MonthlyLineChart({ data }: Props) {
  const formatted = data.map((d) => ({
    ...d,
    label: d.month.slice(0, 7),
  }));

  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={formatted}>
        <XAxis dataKey="label" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis hide />
        <Tooltip
          contentStyle={{ fontSize: 11, borderRadius: 8 }}
          formatter={(v) => [`${v}명`, "태거 수"]}
        />
        <Line
          type="monotone"
          dataKey="tagger_count"
          stroke="#405DE6"
          strokeWidth={2}
          dot={{ r: 3, fill: "#405DE6" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
