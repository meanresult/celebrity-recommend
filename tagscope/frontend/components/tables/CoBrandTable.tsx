"use client";

import { CoBrandRow } from "@/lib/api";

interface Props {
  rows: CoBrandRow[];
  maxTaggerCount: number;
  onRowClick: (row: CoBrandRow) => void;
}

export function CoBrandTable({ rows, maxTaggerCount, onRowClick }: Props) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-100 text-xs text-gray-400">
          <th className="text-left py-3 px-3 w-12">순위</th>
          <th className="text-left py-3 px-3">계정/브랜드명</th>
          <th className="text-left py-3 px-3 w-48">태그한 사람 수</th>
          <th className="text-left py-3 px-3">총 태그 횟수</th>
          <th className="text-left py-3 px-3">비율</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.tagged_account}
            onClick={() => onRowClick(row)}
            className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <td className="py-3 px-3 text-gray-400 font-medium">{row.rank}</td>
            <td className="py-3 px-3 text-[#405DE6] font-medium">@{row.tagged_account}</td>
            <td className="py-3 px-3">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#E1306C] rounded-full"
                    style={{ width: `${maxTaggerCount ? (row.tagger_count / maxTaggerCount) * 100 : 0}%` }}
                  />
                </div>
                <span className="text-gray-700 tabular-nums w-12 text-right">{row.tagger_count.toLocaleString()}명</span>
              </div>
            </td>
            <td className="py-3 px-3 text-gray-700">{row.total_tag_count.toLocaleString()}회</td>
            <td className="py-3 px-3 text-[#E1306C] font-semibold">{row.tagger_ratio}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
