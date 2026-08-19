"use client";

import { useEffect, useState } from "react";
import { Check, Download, X, AlertTriangle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  listExportPresets,
  primaryExtension,
  type ExportTarget,
} from "@/lib/export-presets";
import type { ExportValidationReport } from "@/lib/export-mesh";
import { cn } from "@/lib/utils";

interface ExportWizardDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  projectTitle: string;
  defaultTarget?: ExportTarget;
  onExportComplete?: (target: ExportTarget) => void;
}

type WizardStep = 1 | 2 | 3;

export function ExportWizardDialog({
  open,
  onClose,
  projectId,
  projectTitle,
  defaultTarget = "simodont",
  onExportComplete,
}: ExportWizardDialogProps) {
  const [step, setStep] = useState<WizardStep>(1);
  const [target, setTarget] = useState<ExportTarget>(defaultTarget);
  const [exporting, setExporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ExportValidationReport | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const preset = listExportPresets().find((p) => p.id === target)!;

  useEffect(() => {
    if (open) {
      setTarget(defaultTarget);
      setStep(1);
      setValidation(null);
      setValidateError(null);
      setExportError(null);
      setDone(false);
    }
  }, [open, defaultTarget]);

  if (!open) return null;

  const reset = () => {
    setStep(1);
    setDone(false);
    setExporting(false);
    setValidation(null);
    setValidateError(null);
    setExportError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const runValidation = async () => {
    setValidating(true);
    setValidateError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, validateOnly: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Validation failed.");
      setValidation(data.validation as ExportValidationReport);
      setStep(2);
    } catch (err) {
      setValidateError(err instanceof Error ? err.message : "Validation failed.");
    } finally {
      setValidating(false);
    }
  };

  const runExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error ?? "Export failed.");
      }
      const blob = await res.blob();
      const ext = primaryExtension(preset);
      const safeName = projectTitle.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${safeName}-${target}.${ext}`;
      a.click();
      URL.revokeObjectURL(a.href);
      setDone(true);
      setStep(3);
      onExportComplete?.(target);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-outline-variant bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-outline-variant px-5 py-4">
          <div>
            <h2 className="text-title-lg font-semibold text-on-surface">Export wizard</h2>
            <p className="text-body-sm text-on-surface-variant">{projectTitle}</p>
          </div>
          <button type="button" onClick={handleClose} className="rounded-full p-2 hover:bg-surface-container-high">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex gap-2 border-b border-outline-variant bg-surface-container-low px-5 py-3">
          {(["Destination", "Validate", "Download"] as const).map((label, i) => {
            const n = (i + 1) as WizardStep;
            return (
              <div
                key={label}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-semibold",
                  step === n
                    ? "border-primary-container text-primary-container"
                    : step > n
                      ? "border-outline-variant bg-surface-container-low text-on-surface-variant"
                      : "border-outline-variant text-on-surface-variant"
                )}
              >
                {step > n ? "✓ " : ""}
                {label}
              </div>
            );
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {step === 1 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {listExportPresets().map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setTarget(p.id)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-all",
                    target === p.id
                      ? "border-primary-container bg-primary-container/5 ring-2 ring-primary-container/15"
                      : "border-outline-variant hover:border-primary-container/30"
                  )}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-semibold text-on-surface">{p.label}</span>
                    <Badge variant="outline" className="text-[9px] uppercase">
                      {p.hapticRealism === "visual-only"
                        ? "Visual"
                        : p.hapticRealism === "uniform-drill"
                          ? "Uniform drill"
                          : "Native"}
                    </Badge>
                  </div>
                  <p className="text-body-sm text-on-surface-variant">{p.description}</p>
                </button>
              ))}
            </div>
          )}

          {step === 2 && validation && (
            <div className="space-y-4">
              <ul className="space-y-2 rounded-lg border border-outline-variant bg-surface-container-low p-4">
                <li className="flex items-center gap-2 text-body-sm">
                  {validation.watertight ? (
                    <Check className="h-4 w-4 text-secondary" />
                  ) : (
                    <XCircle className="h-4 w-4 text-amber-600" />
                  )}
                  Watertight: {validation.watertight ? "Yes" : "No"} — {validation.watertightNote}
                </li>
                <li className="flex items-center gap-2 text-body-sm">
                  <Check className="h-4 w-4 text-secondary" />
                  Triangles: {validation.triangleCount.toLocaleString()} /{" "}
                  {validation.maxTriangles.toLocaleString()}
                </li>
                <li className="flex items-center gap-2 text-body-sm">
                  <Check className="h-4 w-4 text-secondary" />
                  Bounding box (mm): {validation.boundingBoxMm.x} × {validation.boundingBoxMm.y} ×{" "}
                  {validation.boundingBoxMm.z}
                </li>
                <li className="flex items-center gap-2 text-body-sm">
                  <Check className="h-4 w-4 text-secondary" />
                  Units: {validation.units}
                </li>
              </ul>
              {validation.warnings.map((w) => (
                <div
                  key={w}
                  className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-body-sm text-amber-950"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>{w}</p>
                </div>
              ))}
              {preset.hapticDisclosure && (
                <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-body-sm text-amber-950">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>{preset.hapticDisclosure}</p>
                </div>
              )}
              {exportError && <p className="text-body-sm text-error">{exportError}</p>}
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-secondary/15">
                <Check className="h-7 w-7 text-secondary" />
              </div>
              <h3 className="text-headline-md font-semibold text-on-surface">Export complete</h3>
              <p className="mt-2 text-body-sm text-on-surface-variant">
                {`${projectTitle}.${primaryExtension(preset)} downloaded for ${preset.label}.`}
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-between gap-2 border-t border-outline-variant px-5 py-4">
          <Button type="button" variant="ghost" onClick={handleClose}>
            {step === 3 ? "Close" : "Cancel"}
          </Button>
          <div className="flex gap-2">
            {validateError && step === 1 && (
              <p className="self-center text-body-sm text-error">{validateError}</p>
            )}
            {step === 2 && (
              <Button type="button" variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
            )}
            {step === 1 && (
              <Button
                type="button"
                className="bg-primary-container text-on-primary"
                disabled={validating}
                onClick={() => void runValidation()}
              >
                {validating ? "Validating…" : "Next: Validate"}
              </Button>
            )}
            {step === 2 && (
              <Button
                type="button"
                className="bg-primary-container text-on-primary"
                disabled={exporting}
                onClick={() => void runExport()}
              >
                <Download className="mr-2 h-4 w-4" />
                {exporting ? "Exporting…" : "Download"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
