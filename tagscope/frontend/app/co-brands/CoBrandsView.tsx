"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandSelector } from "@/components/sidebar/BrandSelector";
import { KpiCards } from "@/components/kpi/KpiCards";
import { CoBrandTable } from "@/components/tables/CoBrandTable";
import { CoBrandDrawer } from "@/components/drawers/CoBrandDrawer";
import { HorizontalBar } from "@/components/charts/HorizontalBar";
import { useFilterStore } from "@/stores/filterStore";
import { api, CoBrandResponse, CoBrandRow } from "@/lib/api";

interface Props {
  allBrands: string[];
}

const DEFAULT_BRANDS = ["amomento.co", "lemaire"];

export function CoBrandsView({ allBrands }: Props) {
  const router = useRouter();
  const { selectedBrands, setPendingBrands, setSelectedBrands } = useFilterStore();
  const [data, setData] = useState<CoBrandResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState<CoBrandRow | null>(null);

  useEffect(() => {
    const defaults = DEFAULT_BRANDS.filter((b) => allBrands.includes(b));
    if (selectedBrands.length === 0) {
      setPendingBrands(defaults);
      setSelectedBrands(defaults);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedBrands.length === 0) { setData(null); return; }
    setLoading(true);
    api.getCoBrands(selectedBrands)
      .then(setData)
      .finally(() => setLoading(false));
  }, [selectedBrands]);

  const kpiCards = data
    ? [
        {
          label: "분석된 계정 수",
          value: `${data.kpi.total_accounts.toLocaleString()}개`,
          note: "선택 브랜드를 태그한 계정",
        },
        {
          label: "발견된 공통 태그 브랜드",
          value: `${data.kpi.co_brand_count.toLocaleString()}개`,
          note: "연관 브랜드 계정",
        },
      ]
    : [];

  const top10 = data?.rows.slice(0, 10) ?? [];
  const maxTaggerCount = data?.rows[0]?.tagger_count ?? 1;

  const handleTaggerClick = (instaId: string) => {
    setSelectedRow(null);
    const params = new URLSearchParams({
      highlight: instaId,
      brands: selectedBrands.join(","),
    });
    router.push(`/taggers?${params.toString()}`);
  };

  return (
    <div className="flex">
      <BrandSelector allBrands={allBrands} />

      <main className="ml-52 flex-1 p-8">
        <h1 className="text-xl font-bold text-gray-900 mb-1">공통 태그 분석</h1>
        <p className="text-sm text-gray-400 mb-6">선택 브랜드를 태그한 사람들이 함께 태그한 계정</p>

        {selectedBrands.length === 0 && (
          <div className="text-sm text-gray-400 mt-16 text-center">
            왼쪽에서 브랜드를 선택하고 적용을 눌러주세요.
          </div>
        )}

        {selectedBrands.length > 0 && (
          <>
            {loading && !data && (
              <div className="text-sm text-gray-400">불러오는 중...</div>
            )}

            {data && data.kpi.total_accounts === 0 && (
              <div className="flex flex-col items-center justify-center mt-24 text-center">
                <p className="text-4xl mb-4">🔍</p>
                <p className="text-base font-semibold text-gray-700 mb-1">공통 태그 계정이 없습니다</p>
                <p className="text-sm text-gray-400">
                  선택한 브랜드를 모두 함께 태그한 계정이 없어요.
                  <br />브랜드 조합을 바꿔보세요.
                </p>
              </div>
            )}

            {data && data.kpi.total_accounts > 0 && (
              <>
                <KpiCards cards={kpiCards} />

                {top10.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mb-6">
                    <h2 className="text-sm font-semibold text-gray-700 mb-1">상위 태그 계정 Top 10</h2>
                    <p className="text-xs text-gray-400 mb-4">X축: 해당 브랜드/계정을 태그한 사람 수</p>
                    <HorizontalBar
                      data={top10.map((r) => ({
                        label: r.tagged_account,
                        value: r.tagger_count,
                      }))}
                    />
                  </div>
                )}

                <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
                  <CoBrandTable
                    rows={data.rows}
                    maxTaggerCount={maxTaggerCount}
                    onRowClick={setSelectedRow}
                  />
                </div>
              </>
            )}
          </>
        )}

      </main>

      <CoBrandDrawer
        row={selectedRow}
        brands={selectedBrands}
        onClose={() => setSelectedRow(null)}
        onTaggerClick={handleTaggerClick}
      />
    </div>
  );
}
