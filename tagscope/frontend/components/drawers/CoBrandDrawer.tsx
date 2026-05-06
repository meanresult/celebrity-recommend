"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, CoBrandDetail, CoBrandRow } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { MonthlyLineChart } from "@/components/charts/MonthlyLineChart";

interface Props {
  row: CoBrandRow | null;
  brands: string[];
  onClose: () => void;
  onTaggerClick?: (instaId: string) => void;
}

export function CoBrandDrawer({ row, brands, onClose, onTaggerClick }: Props) {
  const [detail, setDetail] = useState<CoBrandDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!row) { setDetail(null); return; }
    setLoading(true);
    api.getCoBrandDetail(row.tagged_account, brands)
      .then(setDetail)
      .finally(() => setLoading(false));
  }, [row, brands]);

  if (!row) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <aside className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div>
            <p className="font-semibold text-gray-900">@{row.tagged_account} 를 태그한 사람들</p>
            <p className="text-xs text-gray-400 mt-0.5">{row.tagger_count.toLocaleString()}명이 태그했습니다</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {loading && <p className="text-sm text-gray-400">불러오는 중...</p>}

          {detail && (
            <>
              <section>
                <h3 className="text-xs font-semibold text-gray-500 mb-3">태거 목록</h3>
                <div className="border border-gray-100 rounded-lg overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr className="text-gray-400">
                        <th className="text-left px-3 py-2">계정 ID</th>
                        <th className="text-right px-3 py-2">태그 횟수</th>
                        <th className="text-right px-3 py-2">최근 태그일</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.taggers.map((t) => (
                        <tr key={t.insta_id} className="border-t border-gray-50">
                          <td className="px-3 py-2 text-[#405DE6]">@{t.insta_id}</td>
                          <td className="px-3 py-2 text-right text-gray-700">{t.tag_count}회</td>
                          <td className="px-3 py-2 text-right text-gray-400">{formatDate(t.latest_tag_date)}</td>
                          <td className="px-3 py-2 text-right">
                            <button
                              onClick={() => onTaggerClick?.(t.insta_id)}
                              className="text-[#E1306C] hover:underline"
                            >
                              상세 →
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {detail.monthly.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 mb-3">월별 태그 추이</h3>
                  <MonthlyLineChart data={detail.monthly} />
                </section>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
