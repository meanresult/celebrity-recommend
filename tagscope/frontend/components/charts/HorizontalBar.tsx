"use client";

interface BarItem {
  label: string;
  value: number;
}

interface Props {
  data: BarItem[];
}

export function HorizontalBar({ data }: Props) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-2">
      {data.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-xs text-gray-600 w-28 truncate shrink-0">@{item.label}</span>
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#E1306C] rounded-full"
              style={{ width: `${(item.value / max) * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-6 text-right tabular-nums">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
