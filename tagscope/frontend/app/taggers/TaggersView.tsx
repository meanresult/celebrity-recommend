"use client";

import { useEffect, useState } from "react";
import { BrandSelector } from "@/components/sidebar/BrandSelector";
import { KpiCards } from "@/components/kpi/KpiCards";
import { TaggerTable } from "@/components/tables/TaggerTable";
import { TaggerDrawer } from "@/components/drawers/TaggerDrawer";
import { useFilterStore } from "@/stores/filterStore";
import { api, TaggerResponse, TaggerRow } from "@/lib/api";

interface Props {
  allBrands: string[];
  highlight: string | null;
  initialBrandsParam: string | null;
}

const DEFAULT_BRANDS = ["amomento.co", "lemaire"];

export function TaggersView({ allBrands, highlight, initialBrandsParam }: Props) {
  const { selectedBrands, setPendingBrands, setSelectedBrands } = useFilterStore();
  const [data, setData] = useState<TaggerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [selectedRow, setSelectedRow] = useState<TaggerRow | null>(null);

  useEffect(() => {
    const queryBrands = (initialBrandsParam ?? "")
      .split(",")
      .map((brand) => brand.trim())
      .filter((brand) => brand && allBrands.includes(brand));
    const defaults =
      queryBrands.length > 0
        ? queryBrands
        : DEFAULT_BRANDS.filter((b) => allBrands.includes(b));

    if (selectedBrands.length === 0) {
      setPendingBrands(defaults);
      setSelectedBrands(defaults);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allBrands, initialBrandsParam]);

  // 브랜드가 바뀌면 이전 데이터·페이지·드로어 즉시 초기화
  useEffect(() => {
    setData(null);
    setPage(1);
    setSelectedRow(null);
  }, [selectedBrands]);

  useEffect(() => {
    if (selectedBrands.length === 0) return;
    setLoading(true);
    api.getTaggers(selectedBrands, page)
      .then(setData)
      .finally(() => setLoading(false));
  }, [selectedBrands, page]);

  useEffect(() => {
    if (!highlight || !data) return;

    const matched = data.rows.find((row) => row.insta_id === highlight);
    if (matched) {
      setSelectedRow(matched);
    }
  }, [data, highlight]);

  const kpiCards = data
    ? [
        {
          label: "공통 태그 계정 수",
          value: `${data.kpi.total_accounts.toLocaleString()}개`,
          note: `${selectedBrands.length}개 브랜드 기준`,
        },
        {
          label: "평균 태그 횟수",
          value: `${data.kpi.avg_tag_count.toFixed(1)}회`,
          note: "계정당 평균",
        },
        {
          label: "최다 태그 계정",
          value: `@${data.kpi.top_tagger_name ?? "-"}`,
          note: `${data.kpi.top_tagger_count}회 태그`,
        },
      ]
    : [];

  const maxTagCount = data?.rows[0]?.tag_count ?? 1;

  return (
    <div className="flex">
      <BrandSelector allBrands={allBrands} />

      <main className="ml-52 flex-1 p-8">
        <h1 className="text-xl font-bold text-gray-900 mb-1">브랜드 태거 조회</h1>
        <p className="text-sm text-gray-400 mb-6">선택된 브랜드를 태그한 계정 목록</p>

        {selectedBrands.length === 0 && (
          <div className="text-sm text-gray-400 mt-16 text-center">
            왼쪽에서 브랜드를 선택하고 적용을 눌러주세요.
          </div>
        )}

        {selectedBrands.length > 0 && (
          <>
            {loading && (
              <div className="text-sm text-gray-400 mt-16 text-center">불러오는 중...</div>
            )}

            {!loading && data && data.kpi.total_accounts === 0 && (
              <div className="flex flex-col items-center justify-center mt-24 text-center">
                <p className="text-4xl mb-4">🔍</p>
                <p className="text-base font-semibold text-gray-700 mb-1">공통 태그 계정이 없습니다</p>
                <p className="text-sm text-gray-400">
                  선택한 {selectedBrands.length}개 브랜드를 모두 함께 태그한 계정이 없어요.
                  <br />브랜드 조합을 바꿔보세요.
                </p>
              </div>
            )}

            {!loading && data && data.kpi.total_accounts > 0 && (
              <>
                <KpiCards cards={kpiCards} />
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
                  <TaggerTable
                    rows={data.rows}
                    maxTagCount={maxTagCount}
                    onRowClick={setSelectedRow}
                    page={page}
                    pageSize={data.page_size}
                    total={data.total}
                    onPageChange={(p) => { setPage(p); setSelectedRow(null); }}
                  />
                </div>
              </>
            )}
          </>
        )}
      </main>

      <TaggerDrawer
        row={selectedRow}
        brands={selectedBrands}
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
}
