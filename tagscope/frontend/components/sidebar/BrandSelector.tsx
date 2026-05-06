"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFilterStore } from "@/stores/filterStore";

interface Props {
  allBrands: string[];
}

export function BrandSelector({ allBrands }: Props) {
  const { selectedBrands, pendingBrands, setPendingBrands, apply, reset } = useFilterStore();
  const [search, setSearch] = useState("");

  const filtered = allBrands.filter((b) =>
    b.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (brand: string) => {
    if (pendingBrands.includes(brand)) {
      setPendingBrands(pendingBrands.filter((b) => b !== brand));
    } else {
      setPendingBrands([...pendingBrands, brand]);
    }
  };

  const remove = (brand: string) => {
    setPendingBrands(pendingBrands.filter((b) => b !== brand));
  };

  const isDirty =
    pendingBrands.length !== selectedBrands.length ||
    pendingBrands.some((b) => !selectedBrands.includes(b));

  return (
    <aside className="fixed left-0 top-14 bottom-0 w-52 bg-white border-r border-gray-100 flex flex-col p-4 z-40">
      {/* 현재 적용된 브랜드 */}
      {selectedBrands.length > 0 && (
        <div className="mb-3 p-2 bg-gray-50 rounded-lg">
          <p className="text-[10px] font-semibold text-gray-400 mb-1.5">현재 적용됨</p>
          <div className="flex flex-wrap gap-1">
            {selectedBrands.map((b) => (
              <span
                key={b}
                className="text-[10px] bg-[#E1306C] text-white rounded-full px-2 py-0.5"
              >
                @{b}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs font-semibold text-gray-500 mb-2">브랜드 선택</p>

      <input
        type="text"
        placeholder="브랜드 검색..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 mb-3 outline-none focus:ring-1 focus:ring-[#E1306C]"
      />

      <div className="flex flex-wrap gap-1.5 mb-2 min-h-[32px]">
        {pendingBrands.map((b) => (
          <span
            key={b}
            className="flex items-center gap-1 text-xs bg-[#E1306C]/10 text-[#E1306C] rounded-full px-2 py-0.5"
          >
            @{b}
            <button onClick={() => remove(b)}>
              <X size={10} />
            </button>
          </span>
        ))}
      </div>

      <p className="text-xs text-gray-400 mb-2">
        선택됨: {pendingBrands.length}개
        {isDirty && <span className="ml-1.5 text-amber-500 font-medium">● 미적용</span>}
      </p>

      <div className="flex-1 overflow-y-auto space-y-0.5 mb-4">
        {filtered.map((brand) => {
          const selected = pendingBrands.includes(brand);
          return (
            <button
              key={brand}
              onClick={() => toggle(brand)}
              className={cn(
                "w-full text-left text-xs px-2 py-1.5 rounded-md transition-colors",
                selected
                  ? "bg-[#E1306C]/10 text-[#E1306C] font-medium"
                  : "text-gray-700 hover:bg-gray-50"
              )}
            >
              @{brand}
            </button>
          );
        })}
      </div>

      <div className="flex gap-2">
        <button
          onClick={apply}
          disabled={pendingBrands.length === 0}
          className="flex-1 text-sm bg-[#E1306C] text-white rounded-md py-1.5 font-medium disabled:opacity-40 hover:bg-[#c0275a] transition-colors"
        >
          적용
        </button>
        <button
          onClick={() => reset([])}
          className="flex-1 text-sm border border-gray-200 rounded-md py-1.5 text-gray-600 hover:bg-gray-50 transition-colors"
        >
          초기화
        </button>
      </div>
    </aside>
  );
}
