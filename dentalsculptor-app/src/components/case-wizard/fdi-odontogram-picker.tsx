"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { fdiToothType, toothTypeLabel, type ToothType } from "@/lib/tooth-taxonomy";

/** Permanent dentition — dentist's view (patient right on image left). */
const UPPER_RIGHT = ["18", "17", "16", "15", "14", "13", "12", "11"];
const UPPER_LEFT = ["21", "22", "23", "24", "25", "26", "27", "28"];
const LOWER_RIGHT = ["48", "47", "46", "45", "44", "43", "42", "41"];
const LOWER_LEFT = ["31", "32", "33", "34", "35", "36", "37", "38"];

const FDI_TO_ISO: Record<string, string> = {
  "18": "1", "17": "2", "16": "3", "15": "4", "14": "5", "13": "6", "12": "7", "11": "8",
  "21": "9", "22": "10", "23": "11", "24": "12", "25": "13", "26": "14", "27": "15", "28": "16",
  "48": "32", "47": "31", "46": "30", "45": "29", "44": "28", "43": "27", "42": "26", "41": "25",
  "31": "24", "32": "23", "33": "22", "34": "21", "35": "20", "36": "19", "37": "18", "38": "17",
};

const ISO_TO_FDI: Record<string, string> = Object.fromEntries(
  Object.entries(FDI_TO_ISO).map(([fdi, iso]) => [iso, fdi])
);

export const ALL_FDI = new Set([
  ...UPPER_RIGHT,
  ...UPPER_LEFT,
  ...LOWER_RIGHT,
  ...LOWER_LEFT,
]);

export function normalizeFdiInput(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (/^\d{2}$/.test(trimmed) && ALL_FDI.has(trimmed)) return trimmed;
  if (/^\d{1,2}$/.test(trimmed) && ISO_TO_FDI[trimmed]) return ISO_TO_FDI[trimmed];
  return null;
}

const CHART_IMAGE = "/dental/ISO-3950-system-for-tooth-numbering-16.webp";

function ToothButton({
  fdi,
  selected,
  numbering,
  onSelect,
}: {
  fdi: string;
  selected: boolean;
  numbering: "fdi" | "iso";
  onSelect: (fdi: string) => void;
}) {
  const type = fdiToothType(fdi);
  const label = numbering === "fdi" ? fdi : FDI_TO_ISO[fdi] ?? fdi;

  return (
    <button
      type="button"
      onClick={() => onSelect(fdi)}
      title={`FDI ${fdi} · ${type ? toothTypeLabel(type) : "tooth"}`}
      aria-pressed={selected}
      aria-label={`Select tooth FDI ${fdi}`}
      className={cn(
        "relative z-10 min-h-[2.75rem] min-w-[2.35rem] rounded-lg border px-1 py-1.5 text-center transition-all",
        selected
          ? "border-primary-container bg-primary-container text-on-primary shadow-md ring-2 ring-primary-container/30"
          : "border-outline-variant bg-surface-container-lowest text-on-surface hover:border-primary-container/50 hover:bg-surface-container-low"
      )}
    >
      <span className="block text-[13px] font-bold leading-none">{label}</span>
      <span className="mt-0.5 block text-[8px] font-medium uppercase tracking-wide opacity-80">
        {type ? type.slice(0, 3) : ""}
      </span>
    </button>
  );
}

function ArchRow({
  rightTeeth,
  leftTeeth,
  value,
  numbering,
  onSelect,
}: {
  rightTeeth: string[];
  leftTeeth: string[];
  value?: string;
  numbering: "fdi" | "iso";
  onSelect: (fdi: string) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-1 sm:gap-1.5">
      <div className="flex flex-wrap justify-end gap-1 sm:gap-1.5">
        {rightTeeth.map((fdi) => (
          <ToothButton
            key={fdi}
            fdi={fdi}
            selected={value === fdi}
            numbering={numbering}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="mx-0.5 h-10 w-px shrink-0 bg-outline-variant/80" aria-hidden />
      <div className="flex flex-wrap justify-start gap-1 sm:gap-1.5">
        {leftTeeth.map((fdi) => (
          <ToothButton
            key={fdi}
            fdi={fdi}
            selected={value === fdi}
            numbering={numbering}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

interface FdiOdontogramPickerProps {
  value?: string;
  onChange: (fdi: string) => void;
  onToothTypeChange?: (type: ToothType) => void;
}

export function FdiOdontogramPicker({ value, onChange, onToothTypeChange }: FdiOdontogramPickerProps) {
  const [manualInput, setManualInput] = useState(value ?? "");
  const [numbering, setNumbering] = useState<"fdi" | "iso">("fdi");
  const [manualError, setManualError] = useState<string | null>(null);

  const selectedType = useMemo(() => fdiToothType(value), [value]);

  const selectFdi = (fdi: string) => {
    setManualInput(fdi);
    setManualError(null);
    onChange(fdi);
    const inferred = fdiToothType(fdi);
    if (inferred) onToothTypeChange?.(inferred);
  };

  const applyManual = () => {
    const normalized = normalizeFdiInput(manualInput);
    if (!normalized) {
      setManualError("Enter a valid FDI (11–48) or ISO number (1–32).");
      return;
    }
    selectFdi(normalized);
  };

  return (
    <div className="space-y-4 rounded-xl border border-outline-variant bg-surface-container-low p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-body-sm font-medium text-on-surface">ISO 3950 tooth chart</p>
        <div className="flex rounded-lg border border-outline-variant p-0.5 text-[11px]">
          <button
            type="button"
            onClick={() => setNumbering("fdi")}
            className={cn(
              "rounded-md px-2.5 py-1 font-semibold transition-colors",
              numbering === "fdi"
                ? "bg-primary-container text-on-primary"
                : "text-on-surface-variant hover:text-on-surface"
            )}
          >
            FDI
          </button>
          <button
            type="button"
            onClick={() => setNumbering("iso")}
            className={cn(
              "rounded-md px-2.5 py-1 font-semibold transition-colors",
              numbering === "iso"
                ? "bg-primary-container text-on-primary"
                : "text-on-surface-variant hover:text-on-surface"
            )}
          >
            ISO 1–32
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-outline-variant/70 bg-white p-2 sm:p-3">
        <div className="relative mx-auto aspect-[4/3] w-full max-w-xl min-h-[200px]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={CHART_IMAGE}
            alt="ISO 3950 permanent dentition chart showing all tooth types and numbers"
            className="h-full w-full object-contain"
            loading="eager"
            decoding="async"
          />
        </div>
        <p className="mt-2 text-center text-[10px] text-on-surface-variant">
          Reference chart — tap your tooth number below to match your model.
        </p>
      </div>

      <div className="space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
          Upper arch (maxilla)
        </p>
        <ArchRow
          rightTeeth={UPPER_RIGHT}
          leftTeeth={UPPER_LEFT}
          value={value}
          numbering={numbering}
          onSelect={selectFdi}
        />
        <p className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
          Lower arch (mandible)
        </p>
        <ArchRow
          rightTeeth={LOWER_RIGHT}
          leftTeeth={LOWER_LEFT}
          value={value}
          numbering={numbering}
          onSelect={selectFdi}
        />
      </div>

      <div className="rounded-lg border border-outline-variant/70 bg-surface-container-lowest p-3">
        <label htmlFor="fdi-manual" className="mb-1.5 block text-body-sm font-medium text-on-surface">
          Know your tooth number?
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            id="fdi-manual"
            type="text"
            inputMode="numeric"
            maxLength={2}
            placeholder={numbering === "fdi" ? "e.g. 16 or 11" : "e.g. 3 or 8"}
            value={manualInput}
            onChange={(e) => {
              setManualInput(e.target.value.replace(/[^\d]/g, "").slice(0, 2));
              setManualError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                applyManual();
              }
            }}
            className="w-28 rounded-lg border border-outline-variant bg-background px-3 py-2 text-body-sm"
          />
          <button
            type="button"
            onClick={applyManual}
            className="rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-body-sm font-medium text-on-surface hover:bg-surface-container"
          >
            Apply
          </button>
        </div>
        {manualError && (
          <p className="mt-1.5 text-[11px] text-error" role="alert">
            {manualError}
          </p>
        )}
      </div>

      {value && (
        <div className="rounded-lg bg-primary-container/10 px-3 py-2.5 text-body-sm text-on-surface">
          <span className="font-semibold text-primary-container">FDI {value}</span>
          {selectedType && (
            <span className="ml-2 text-on-surface">
              → {toothTypeLabel(selectedType)} (auto-filled in tooth type)
            </span>
          )}
          {FDI_TO_ISO[value] && (
            <span className="ml-2 text-on-surface-variant">· ISO {FDI_TO_ISO[value]}</span>
          )}
        </div>
      )}
    </div>
  );
}
