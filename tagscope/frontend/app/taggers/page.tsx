import { api } from "@/lib/api";
import { TaggersView } from "./TaggersView";

interface PageProps {
  searchParams?: {
    highlight?: string;
    brands?: string;
  };
}

export default async function TaggersPage({ searchParams }: PageProps) {
  let allBrands: string[] = [];
  try {
    allBrands = await api.getBrands();
  } catch {}

  const highlight =
    typeof searchParams?.highlight === "string" ? searchParams.highlight : null;
  const initialBrandsParam =
    typeof searchParams?.brands === "string" ? searchParams.brands : null;

  return (
    <TaggersView
      allBrands={allBrands}
      highlight={highlight}
      initialBrandsParam={initialBrandsParam}
    />
  );
}
