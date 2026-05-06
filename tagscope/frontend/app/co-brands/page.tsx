import { api } from "@/lib/api";
import { CoBrandsView } from "./CoBrandsView";

export default async function CoBrandsPage() {
  let allBrands: string[] = [];
  try {
    allBrands = await api.getBrands();
  } catch {}

  return <CoBrandsView allBrands={allBrands} />;
}
