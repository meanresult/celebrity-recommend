interface KpiCard {
  label: string;
  value: string;
  note: string;
}

interface Props {
  cards: KpiCard[];
}

export function KpiCards({ cards }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-xl border border-gray-100 shadow-sm p-5"
        >
          <p className="text-xs text-gray-400 mb-1">{card.label}</p>
          <p className="text-3xl font-bold text-gray-900 leading-tight">{card.value}</p>
          <p className="text-xs text-gray-400 mt-1">{card.note}</p>
        </div>
      ))}
    </div>
  );
}
