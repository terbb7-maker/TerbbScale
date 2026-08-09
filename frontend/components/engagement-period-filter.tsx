"use client";

export type EngagementPeriod = "today" | "yesterday" | "month" | "custom";

const options: Array<{ value: EngagementPeriod; label: string }> = [
  { value: "today", label: "Hoje" },
  { value: "yesterday", label: "Ontem" },
  { value: "month", label: "Mês" },
  { value: "custom", label: "Personalizado" },
];

type Props = {
  period: EngagementPeriod;
  dateFrom: string;
  dateTo: string;
  maxDate: string;
  onPeriodChange: (period: EngagementPeriod) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
};

export function EngagementPeriodFilter({
  period,
  dateFrom,
  dateTo,
  maxDate,
  onPeriodChange,
  onDateFromChange,
  onDateToChange,
}: Props) {
  const invalidRange = dateFrom > dateTo;

  return (
    <div className="mt-4">
      <div className="grid grid-cols-2 gap-1 rounded-xl border bg-zinc-950/70 p-1">
        {options.map((option) => (
          <button
            className={`rounded-lg px-2 py-2 text-xs font-medium ${
              period === option.value
                ? "bg-violet-500/15 text-violet-300"
                : "text-zinc-500 hover:bg-zinc-800/60 hover:text-zinc-300"
            }`}
            key={option.value}
            onClick={() => onPeriodChange(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      {period === "custom" && (
        <div className="mt-3 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-zinc-600">
            De
            <input
              className="input mt-1 px-2 py-2 text-xs"
              max={dateTo || maxDate}
              onChange={(event) => onDateFromChange(event.target.value)}
              type="date"
              value={dateFrom}
            />
          </label>
          <label className="text-[11px] text-zinc-600">
            Até
            <input
              className="input mt-1 px-2 py-2 text-xs"
              max={maxDate}
              min={dateFrom}
              onChange={(event) => onDateToChange(event.target.value)}
              type="date"
              value={dateTo}
            />
          </label>
          {invalidRange && (
            <p className="col-span-2 text-[11px] text-red-400">
              A data inicial precisa ser anterior à data final.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
