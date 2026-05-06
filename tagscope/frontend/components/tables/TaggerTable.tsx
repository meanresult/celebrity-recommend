"use client";

import { TaggerRow } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface Props {
  rows: TaggerRow[];
  maxTagCount: number;
  onRowClick: (row: TaggerRow) => void;
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function TaggerTable({
  rows,
  maxTagCount,
  onRowClick,
  page,
  pageSize,
  total,
  onPageChange,
}: Props) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs text-gray-400">
            <th className="text-left py-3 px-3 w-12">순위</th>
            <th className="text-left py-3 px-3 w-8"></th>
            <th className="text-left py-3 px-3">계정 ID</th>
            <th className="text-left py-3 px-3">표시 이름</th>
            <th className="text-left py-3 px-3 w-40">태그 횟수</th>
            <th className="text-left py-3 px-3">최근 태그일</th>
            <th className="text-left py-3 px-3">함께 태그한 브랜드</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.insta_id}
              onClick={() => onRowClick(row)}
              className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <td className="py-3 px-3 text-gray-400 font-medium">{row.rank}</td>
              <td className="py-3 px-3">
                <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-gray-400 text-xs">
                  {row.insta_name.charAt(0).toUpperCase()}
                </div>
              </td>
              <td className="py-3 px-3 text-[#405DE6] font-medium">@{row.insta_id}</td>
              <td className="py-3 px-3 text-gray-700">{row.insta_name}</td>
              <td className="py-3 px-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#E1306C] rounded-full"
                      style={{ width: `${maxTagCount ? (row.tag_count / maxTagCount) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="text-gray-700 tabular-nums w-6 text-right">{row.tag_count}</span>
                </div>
              </td>
              <td className="py-3 px-3 text-gray-400">{formatDate(row.latest_tag_date)}</td>
              <td className="py-3 px-3 text-gray-500">{row.other_brand_count}개</td>
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-6">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="text-xs px-3 py-1.5 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            &lt; 이전
          </button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`text-xs w-8 h-8 rounded border transition-colors ${
                p === page
                  ? "bg-[#E1306C] text-white border-[#E1306C]"
                  : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              {p}
            </button>
          ))}
          {totalPages > 7 && <span className="text-gray-400 text-xs">...</span>}
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages}
            className="text-xs px-3 py-1.5 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
          >
            다음 &gt;
          </button>
        </div>
      )}
    </div>
  );
}
