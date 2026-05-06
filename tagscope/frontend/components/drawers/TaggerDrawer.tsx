"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink } from "lucide-react";
import { api, TaggerDetail, TaggerRow } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { HorizontalBar } from "@/components/charts/HorizontalBar";

interface Props {
  row: TaggerRow | null;
  brands: string[];
  onClose: () => void;
}

export function TaggerDrawer({ row, brands, onClose }: Props) {
  const [detail, setDetail] = useState<TaggerDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!row) { setDetail(null); return; }
    setLoading(true);
    api.getTaggerDetail(row.insta_id, brands)
      .then(setDetail)
      .finally(() => setLoading(false));
  }, [row, brands]);

  if (!row) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <aside className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#E1306C]/20 to-[#405DE6]/20 flex items-center justify-center text-[#E1306C] font-bold">
              {row.insta_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-semibold text-gray-900">@{row.insta_id}</p>
              <a
                href={`https://www.instagram.com/${row.insta_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#405DE6] flex items-center gap-0.5 hover:underline"
              >
                프로필 보기 <ExternalLink size={10} />
              </a>
            </div>
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
                <h3 className="text-xs font-semibold text-gray-500 mb-3">
                  이 계정이 가장 많이 태그한 브랜드 Top 10
                </h3>
                <HorizontalBar
                  data={detail.top_brands.map((b) => ({
                    label: b.brand,
                    value: b.count,
                  }))}
                />
              </section>

              <section>
                <h3 className="text-xs font-semibold text-gray-500 mb-3">최근 게시물</h3>
                <div className="space-y-3">
                  {detail.recent_posts.map((post) => (
                    <div key={post.post_id} className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-400 mb-1">{formatDate(post.post_date)}</p>
                      <p className="text-xs text-gray-600 mb-2">
                        태그: {post.tagged_accounts !== "-" ? post.tagged_accounts : "없음"}
                      </p>
                      {post.full_link && (
                        <a
                          href={post.full_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#405DE6] flex items-center gap-0.5 hover:underline"
                        >
                          게시물 보기 <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  ))}
                  {detail.recent_posts.length === 0 && (
                    <p className="text-xs text-gray-400">게시물 없음</p>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
