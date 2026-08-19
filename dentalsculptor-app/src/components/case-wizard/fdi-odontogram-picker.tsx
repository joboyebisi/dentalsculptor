"use client";

import { cn } from "@/lib/utils";

/** FDI permanent dentition — simplified odontogram (TrueTeethLab-style). */
const UPPER = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"];
const LOWER = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"];

interface FdiOdontogramPickerProps {
  value?: string;
  onChange: (fdi: string) => void;
}

export function FdiOdontogramPicker({ value, onChange }: FdiOdontogramPickerProps) {
  const renderRow = (teeth: string[], label: string) => (
    <div>
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
        {label}
      </p>
      <div className="flex flex-wrap gap-1">
        {teeth.map((fdi) => (
          <button
            key={fdi}
            type="button"
            onClick={() => onChange(fdi)}
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-md border text-[11px] font-semibold transition-colors",
              value === fdi
                ? "border-primary-container bg-primary-container text-on-primary"
                : "border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:border-primary-container/40"
            )}
            title={`FDI ${fdi}`}
          >
            {fdi.slice(0, 1)}
            <span className="text-[9px] opacity-80">{fdi.slice(1)}</span>
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-3 rounded-xl border border-outline-variant bg-surface-container-low p-4">
      {renderRow(UPPER, "Upper (maxilla)")}
      <div className="border-t border-outline-variant/60" />
      {renderRow(LOWER, "Lower (mandible)")}
      {value && (
        <p className="text-body-sm text-on-surface">
          Selected: <span className="font-semibold text-primary-container">FDI {value}</span>
        </p>
      )}
    </div>
  );
}
