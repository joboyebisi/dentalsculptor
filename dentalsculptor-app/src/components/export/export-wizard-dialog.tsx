"use client";

import { useEffect, useState, useMemo } from "react";
import { Check, Download, X, AlertTriangle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  listExportPresets,
  primaryExtension,
  type ExportTarget,
} from "@/lib/export-presets";
import type { ExportValidationReport } from "@/lib/export-mesh";
import type { ExportScope, MeshExportFormat } from "@/lib/export-mesh";
import { cn } from "@/lib/utils";
import type { CaseRecipe } from "@/lib/clinical-case-params";
import type { CaseTemplate } from "@/lib/case-templates";
import { getExportPreset } from "@/lib/export-presets";
import { listExportAssetOptions, type ExportAssetId } from "@/lib/export-asset-options";

const DIRECT_FORMATS: { id: MeshExportFormat; label: string; hint: string }[] = [
  { id: "stl", label: "STL", hint: "Simulators, 3D print (mm)" },
  { id: "obj", label: "OBJ", hint: "CAD / Blender interchange" },
  { id: "glb", label: "GLB", hint: "Web viewer, Quest" },
  { id: "ply", label: "PLY", hint: "Research / point tools" },
];

interface ExportWizardDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  projectTitle: string;
  modelUrl?: string | null;
  defaultTarget?: ExportTarget;
  hasPartSelection?: boolean;
  selectedPartCount?: number;
  selectedCase?: CaseTemplate | null;
  caseRecipe?: CaseRecipe | null;
  sourceImageUrl?: string | null;
  onExportComplete?: (target: ExportTarget) => void;
}

type WizardStep = 1 | 2 | 3;

export function ExportWizardDialog({
  open,
  onClose,
  projectId,
  projectTitle,
  defaultTarget = "simodont",
  modelUrl,
  hasPartSelection = false,
  selectedPartCount = 0,
  selectedCase = null,
  caseRecipe = null,
  sourceImageUrl = null,
  onExportComplete,
}: ExportWizardDialogProps) {
  const [step, setStep] = useState<WizardStep>(1);
  const [target, setTarget] = useState<ExportTarget>(defaultTarget);
  const [outputFormat, setOutputFormat] = useState<MeshExportFormat>("stl");
  const [scope, setScope] = useState<ExportScope>("full");
  const [selectedAssets, setSelectedAssets] = useState<ExportAssetId[]>([]);
  const [exporting, setExporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ExportValidationReport | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const preset = listExportPresets().find((p) => p.id === target)!;
  const exportPreset = getExportPreset(target);
  const allowedFormats = DIRECT_FORMATS.filter(
    (f) =>
      f.id === "obj" ||
      exportPreset.formats.includes(f.id as "stl" | "ply" | "glb" | "zip")
  );
  const assetOptions = useMemo(
    () =>
      listExportAssetOptions({
        target,
        outputFormat,
        hasModel: Boolean(modelUrl),
        sourceImageUrl,
        selectedCase,
        caseRecipe,
        jawPlaced: false,
      }),
    [target, outputFormat, modelUrl, sourceImageUrl, selectedCase, caseRecipe]
  );

  useEffect(() => {
    if (open) {
      setTarget(defaultTarget);
      const defFmt = defaultTarget === "meta-quest" ? "glb" : "stl";
      setOutputFormat(defFmt);
      setScope("full");
      setStep(1);
      setValidation(null);
      setValidateError(null);
      setExportError(null);
      setDone(false);
    }
  }, [open, defaultTarget]);

  useEffect(() => {
    setSelectedAssets(
      assetOptions.filter((a) => a.defaultSelected && a.available).map((a) => a.id)
    );
  }, [assetOptions]);

  useEffect(() => {
    const preset = listExportPresets().find((p) => p.id === target);
    if (preset) {
      const preferred = preset.formats.find((f) => f !== "zip") as MeshExportFormat | undefined;
      if (preferred) setOutputFormat(preferred);
    }
  }, [target]);

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
        body: JSON.stringify({
          target,
          validateOnly: true,
          outputFormat,
          scope,
          modelUrl: modelUrl ?? undefined,
        }),
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
      const assetsToSend = selectedAssets.includes("mesh-primary")
        ? selectedAssets
        : (["mesh-primary", ...selectedAssets] as ExportAssetId[]);
      const needsBundle =
        assetsToSend.length > 1 ||
        assetsToSend.some((id) =>
          ["source-photo", "reference-glb", "readme", "mesh-stl"].includes(id)
        ) ||
        target === "teaching-bundle";

      const res = await fetch(`/api/projects/${projectId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target,
          outputFormat,
          scope,
          modelUrl: modelUrl ?? undefined,
          assets: assetsToSend,
          bundle: needsBundle,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error ?? "Export failed.");
      }
      const blob = await res.blob();
      const contentType = res.headers.get("Content-Type") ?? "";
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const match = disposition.match(/filename="([^"]+)"/);
      const ext = contentType.includes("zip")
        ? "zip"
        : contentType.includes("gltf")
          ? "glb"
          : outputFormat;
      const safeName = projectTitle.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 64);
      const downloadName = match?.[1] ?? `${safeName}-${target}.${ext}`;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = downloadName;
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
            <div className="space-y-6">
              <div>
                <p className="mb-2 text-label-caps font-semibold text-on-surface-variant">
                  What to export
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setScope("full")}
                    className={cn(
                      "rounded-lg border px-4 py-2 text-body-sm transition-colors",
                      scope === "full"
                        ? "border-primary-container bg-primary-container/10 text-primary-container"
                        : "border-outline-variant hover:border-primary-container/30"
                    )}
                  >
                    Full model
                  </button>
                  <button
                    type="button"
                    onClick={() => setScope("selection")}
                    disabled={!hasPartSelection}
                    className={cn(
                      "rounded-lg border px-4 py-2 text-body-sm transition-colors",
                      scope === "selection"
                        ? "border-primary-container bg-primary-container/10 text-primary-container"
                        : "border-outline-variant hover:border-primary-container/30",
                      !hasPartSelection && "cursor-not-allowed opacity-50"
                    )}
                  >
                    Selected parts ({selectedPartCount})
                  </button>
                </div>
                {!hasPartSelection && (
                  <p className="mt-1 text-[11px] text-on-surface-variant">
                    Enable parts in the properties panel to export a selection.
                  </p>
                )}
              </div>

              <div>
                <p className="mb-2 text-label-caps font-semibold text-on-surface-variant">
                  Include in download
                </p>
                <div className="space-y-2">
                  {assetOptions.map((asset) => {
                    const checked = selectedAssets.includes(asset.id);
                    const recommended = asset.recommendedFor?.includes(target);
                    return (
                      <label
                        key={asset.id}
                        className={cn(
                          "flex cursor-pointer gap-3 rounded-lg border p-3",
                          !asset.available && "cursor-not-allowed opacity-50",
                          checked
                            ? "border-primary-container bg-primary-container/5"
                            : "border-outline-variant"
                        )}
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          disabled={!asset.available || asset.id === "mesh-primary"}
                          checked={asset.id === "mesh-primary" ? true : checked}
                          onChange={() => {
                            if (asset.id === "mesh-primary") return;
                            setSelectedAssets((prev) =>
                              checked
                                ? prev.filter((id) => id !== asset.id)
                                : [...prev, asset.id]
                            );
                          }}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-2 text-body-sm font-medium text-on-surface">
                            {asset.label}
                            {recommended && (
                              <Badge variant="outline" className="text-[9px]">
                                Recommended
                              </Badge>
                            )}
                          </span>
                          <span className="mt-0.5 block text-[11px] text-on-surface-variant">
                            {asset.available
                              ? asset.description
                              : (asset.unavailableReason ?? "Not available")}
                          </span>
                        </span>
                      </label>
                    );
                  })}
                </div>
                {["simodont", "simtocare", "virteasy"].includes(target) && (
                  <p className="mt-2 text-[11px] text-on-surface-variant">
                    Simulators typically need only the watertight STL/PLY mesh — skip GLB and source photo unless
                    your LMS also needs them.
                  </p>
                )}
              </div>

              <div>
                <p className="mb-2 text-label-caps font-semibold text-on-surface-variant">
                  File format
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(allowedFormats.length ? allowedFormats : DIRECT_FORMATS).map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setOutputFormat(f.id)}
                      className={cn(
                        "rounded-lg border p-3 text-left transition-colors",
                        outputFormat === f.id
                          ? "border-primary-container bg-primary-container/10 ring-2 ring-primary-container/15"
                          : "border-outline-variant hover:border-primary-container/30"
                      )}
                    >
                      <span className="font-semibold text-on-surface">{f.label}</span>
                      <p className="mt-0.5 text-[10px] text-on-surface-variant">{f.hint}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-label-caps font-semibold text-on-surface-variant">
                  Destination preset
                </p>
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
              </div>
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
                {`${projectTitle}.${outputFormat} downloaded for ${preset.label}.`}
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
