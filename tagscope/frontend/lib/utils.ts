import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  return dateStr.slice(0, 10);
}

export function hoursAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  const diff = (Date.now() - new Date(dateStr).getTime()) / 3600000;
  if (diff < 1) return "방금 전";
  if (diff < 24) return `${Math.floor(diff)}시간 전`;
  return `${Math.floor(diff / 24)}일 전`;
}

export function freshnessTone(lastLoadedAt: string | null, latestPostDate: string | null) {
  if (!lastLoadedAt || !latestPostDate) return "neutral";
  const hoursSince = (Date.now() - new Date(lastLoadedAt).getTime()) / 3600000;
  const daysSince = (Date.now() - new Date(latestPostDate).getTime()) / 86400000;
  if (hoursSince <= 12 && daysSince <= 1) return "healthy";
  if (hoursSince <= 24 && daysSince <= 2) return "watch";
  return "stale";
}
