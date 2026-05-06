import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TopNav } from "@/components/layout/TopNav";
import { api } from "@/lib/api";

const inter = Inter({ subsets: ["latin"] });

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "TagScope",
  description: "Instagram brand tagger analytics",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let lastLoadedAt: string | null = null;
  let latestPostDate: string | null = null;
  try {
    const freshness = await api.getFreshness();
    lastLoadedAt = freshness.last_loaded_at;
    latestPostDate = freshness.latest_post_date;
  } catch {}

  return (
    <html lang="ko">
      <body className={inter.className}>
        <TopNav lastLoadedAt={lastLoadedAt} latestPostDate={latestPostDate} />
        <div className="pt-14">{children}</div>
      </body>
    </html>
  );
}
