"use client";

import { useMemo } from "react";
import type { ClinicalParameterField } from "@/lib/clinical-case-params";
import type { ClinicalParameterValues } from "@/lib/case-recipe-utils";
import { cn } from "@/lib/utils";
import { FdiOdontogramPicker } from "@/components/case-wizard/fdi-odontogram-picker";
import { fdiToothType } from "@/lib/tooth-taxonomy";
import {
  applyLibraryHintsToClinicalValues,
  peekGenerationLibraryHints,
} from "@/lib/generation-library-hints";

interface CaseWizardClinicalFormProps {
  fields: ClinicalParameterField[];
  values: ClinicalParameterValues;
  onChange: (values: ClinicalParameterValues) => void;
  className?: string;
}

function FieldLabel({ field }: { field: ClinicalParameterField }) {
  return (
    <label className="mb-1.5 block text-body-sm font-medium text-on-surface">
      {field.label}
      {field.required && <span className="text-error"> *</span>}
    </label>
  );
}

export function CaseWizardClinicalForm({
  fields,
  values,
  onChange,
  className,
}: CaseWizardClinicalFormProps) {
  const setValue = (id: string, value: string | number | boolean | string[]) => {
    onChange({ ...values, [id]: value });
  };

  const grouped = useMemo(() => {
    const primary = fields.filter((f) => f.type === "fdi-tooth");
    const clinical = fields.filter((f) => f.type !== "fdi-tooth");
    return { primary, clinical };
  }, [fields]);

  return (
    <div className={cn("space-y-6", className)}>
      {grouped.primary.map((field) => (
        <div key={field.id}>
          <FieldLabel field={field} />
          <FdiOdontogramPicker
            value={typeof values[field.id] === "string" ? (values[field.id] as string) : undefined}
            onChange={(fdi) => {
              setValue(field.id, fdi);
              const inferred = fdiToothType(fdi);
              if (inferred && fields.some((f) => f.id === "toothType")) {
                setValue("toothType", inferred);
              }
            }}
          />
          {fields.some((f) => f.id === "toothType") && values.toothType && (
            <p className="mt-2 text-body-sm text-on-surface">
              Tooth type:{" "}
              <span className="font-semibold capitalize text-primary-container">
                {String(values.toothType)}
              </span>{" "}
              <span className="text-on-surface-variant">(from FDI chart)</span>
            </p>
          )}
          {field.helpText && (
            <p className="mt-1 text-[11px] text-on-surface-variant">{field.helpText}</p>
          )}
        </div>
      ))}

      <div className="grid gap-4 sm:grid-cols-2">
        {grouped.clinical.map((field) => (
          <div
            key={field.id}
            className={cn(field.type === "multiselect" && "sm:col-span-2")}
          >
            <FieldLabel field={field} />

            {(field.type === "select" ||
              field.type === "surface" ||
              field.type === "depth" ||
              field.type === "tissue-involvement" ||
              field.type === "pulp-proximity") && (
              <select
                className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-sm text-on-surface"
                value={typeof values[field.id] === "string" ? (values[field.id] as string) : ""}
                onChange={(e) => setValue(field.id, e.target.value)}
              >
                <option value="">Select…</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}

            {field.type === "multiselect" && (
              <div className="flex flex-wrap gap-2">
                {field.options?.map((opt) => {
                  const selected = Array.isArray(values[field.id])
                    ? (values[field.id] as string[]).includes(opt.value)
                    : false;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => {
                        const current = Array.isArray(values[field.id])
                          ? (values[field.id] as string[])
                          : [];
                        const next = selected
                          ? current.filter((v) => v !== opt.value)
                          : [...current, opt.value];
                        setValue(field.id, next);
                      }}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        selected
                          ? "border-primary-container bg-primary-container/15 text-primary-container"
                          : "border-outline-variant text-on-surface-variant hover:bg-surface-container-low"
                      )}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            )}

            {field.type === "number" && (() => {
              const raw = values[field.id];
              const numDisplay: number | "" =
                typeof raw === "number"
                  ? raw
                  : raw === undefined || raw === ""
                    ? ""
                    : Number(raw);
              return (
              <input
                type="number"
                step="0.1"
                min={0}
                className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-sm"
                value={numDisplay}
                onChange={(e) => {
                  const next = e.target.value === "" ? "" : Number(e.target.value);
                  setValue(field.id, next);
                }}
              />
              );
            })()}

            {(field.type === "text" || field.type === "site") && (
              <input
                type="text"
                className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-body-sm"
                placeholder={field.helpText}
                value={typeof values[field.id] === "string" ? (values[field.id] as string) : ""}
                onChange={(e) => setValue(field.id, e.target.value)}
              />
            )}

            {field.helpText && field.type !== "fdi-tooth" && (
              <p className="mt-1 text-[11px] text-on-surface-variant">{field.helpText}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function defaultClinicalValues(fields: ClinicalParameterField[]): ClinicalParameterValues {
  const values: ClinicalParameterValues = {};
  for (const field of fields) {
    if (field.type === "number" && field.id === "occlusalReductionMm") values[field.id] = 1.5;
    else if (field.type === "multiselect") values[field.id] = [];
    else values[field.id] = "";
  }
  return applyLibraryHintsToClinicalValues(values, fields, peekGenerationLibraryHints());
}
