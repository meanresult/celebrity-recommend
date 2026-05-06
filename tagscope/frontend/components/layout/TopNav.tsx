"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn, freshnessTone, hoursAgo } from "@/lib/utils";

interface Props {
  lastLoadedAt: string | null;
  latestPostDate: string | null;
}

export function TopNav({ lastLoadedAt, latestPostDate }: Props) {
  const path = usePathname();
  const tone = freshnessTone(lastLoadedAt, latestPostDate);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-white border-b border-gray-100 flex items-center px-6">
      <div className="flex items-center gap-2 w-48">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#E1306C] to-[#405DE6]" />
        <span className="font-bold text-lg tracking-tight">TagScope</span>
      </div>

      <nav className="flex-1 flex justify-center gap-8">
        <Link
          href="/taggers"
          className={cn(
            "text-sm font-medium pb-1 border-b-2 transition-colors",
            path === "/taggers"
              ? "border-[#E1306C] text-[#E1306C]"
              : "border-transparent text-gray-500 hover:text-gray-900"
          )}
        >
          브랜드 태거 조회
        </Link>
        <Link
          href="/co-brands"
          className={cn(
            "text-sm font-medium pb-1 border-b-2 transition-colors",
            path === "/co-brands"
              ? "border-[#E1306C] text-[#E1306C]"
              : "border-transparent text-gray-500 hover:text-gray-900"
          )}
        >
          공통 태그 분석
        </Link>
      </nav>

      <div className="w-48 flex justify-end items-center gap-1.5">
        <span className={cn("w-2 h-2 rounded-full", tone === "healthy" ? "bg-green-500" : tone === "watch" ? "bg-yellow-500" : "bg-red-400")} />
        <span className="text-xs text-gray-400">마지막 수집: {hoursAgo(lastLoadedAt)}</span>
      </div>
    </header>
  );
}
