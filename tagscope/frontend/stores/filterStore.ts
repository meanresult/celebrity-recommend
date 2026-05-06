import { create } from "zustand";

interface FilterStore {
  selectedBrands: string[];
  pendingBrands: string[];
  setSelectedBrands: (brands: string[]) => void;
  setPendingBrands: (brands: string[]) => void;
  apply: () => void;
  reset: (defaultBrands: string[]) => void;
}

export const useFilterStore = create<FilterStore>((set) => ({
  selectedBrands: [],
  pendingBrands: [],
  setSelectedBrands: (brands) => set({ selectedBrands: brands }),
  setPendingBrands: (brands) => set({ pendingBrands: brands }),
  apply: () => set((s) => ({ selectedBrands: s.pendingBrands })),
  reset: (defaultBrands) =>
    set({ pendingBrands: defaultBrands, selectedBrands: defaultBrands }),
}));
