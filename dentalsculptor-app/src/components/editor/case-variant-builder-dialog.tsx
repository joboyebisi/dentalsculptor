"use client";

import { useMemo, useState } from "react";
import { Layers3, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CASE_VARIANT_PRESETS, type CaseVariantPreset, type CaseVariantRecipe, type VariantCase } from "@/lib/case-variant-recipes";

const CASES: { id: VariantCase; label: string; note: string }[] = [
  { id: "fracture", label: "Fracture", note: "Deterministic removal" },
  { id: "class-i", label: "Class I cavity", note: "Deterministic removal" },
  { id: "endo", label: "Endo access", note: "External opening" },
  { id: "caries", label: "Caries", note: "Appearance or excavation" },
  { id: "crown", label: "Crown reduction", note: "Advanced" },
  { id: "cusp-restoration", label: "Restore cusp", note: "Generative" },
];

export function CaseVariantBuilderDialog({ open, onClose, onPrepare }: { open: boolean; onClose: () => void; onPrepare: (preset: CaseVariantPreset, recipe: CaseVariantRecipe) => void }) {
  const [caseId, setCaseId] = useState<VariantCase>("fracture");
  const available = useMemo(() => CASE_VARIANT_PRESETS.filter((item) => item.caseId === caseId), [caseId]);
  const [presetId, setPresetId] = useState("fracture-small-chip");
  const preset = CASE_VARIANT_PRESETS.find((item) => item.id === presetId && item.caseId === caseId) ?? available[0];
  const [severity, setSeverity] = useState<CaseVariantRecipe["severity"]>("small");
  const [angleDeg, setAngleDeg] = useState(35);
  const [depthMm, setDepthMm] = useState(1.5);
  const [targetSurface, setTargetSurface] = useState("occlusal");
  if (!open) return null;

  function selectCase(next: VariantCase) {
    setCaseId(next);
    const first = CASE_VARIANT_PRESETS.find((item) => item.caseId === next);
    if (first) { setPresetId(first.id); setSeverity(first.defaultSeverity); }
  }

  return <div className="fixed inset-0 z-[100] flex items-center justify-center bg-on-surface/65 p-4 backdrop-blur-sm"><div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-outline-variant bg-surface shadow-2xl"><header className="flex items-start justify-between border-b border-outline-variant px-6 py-4"><div><h2 className="flex items-center gap-2 text-title-lg font-semibold"><Layers3 className="h-5 w-5 text-primary-container" />Create a teaching variant</h2><p className="mt-1 text-body-sm text-on-surface-variant">The generated tooth remains the master. This recipe creates a separate, reversible case variant.</p></div><button type="button" onClick={onClose} className="rounded-full p-2 hover:bg-surface-container-high" aria-label="Close"><X className="h-5 w-5" /></button></header><div className="grid min-h-0 flex-1 md:grid-cols-[220px_1fr]"><aside className="overflow-y-auto border-r border-outline-variant bg-surface-container-low p-3">{CASES.map((item) => <button key={item.id} type="button" onClick={() => selectCase(item.id)} className={cn("mb-1 w-full rounded-xl px-3 py-2.5 text-left", caseId === item.id ? "bg-primary-container text-on-primary" : "hover:bg-surface-container-high")}><span className="block text-body-sm font-semibold">{item.label}</span><span className={cn("text-[10px]", caseId === item.id ? "text-on-primary/75" : "text-on-surface-variant")}>{item.note}</span></button>)}</aside><main className="overflow-y-auto p-5"><h3 className="text-label-caps text-on-surface-variant">Choose one preset</h3><div className="mt-3 grid gap-3 sm:grid-cols-2">{available.map((item) => <button key={item.id} type="button" onClick={() => { setPresetId(item.id); setSeverity(item.defaultSeverity); }} className={cn("rounded-xl border p-4 text-left", preset?.id === item.id ? "border-primary-container bg-primary-container/5 ring-2 ring-primary-container/15" : "border-outline-variant hover:border-primary-container/40")}><span className="font-semibold">{item.label}</span><span className="mt-1 block text-body-sm text-on-surface-variant">{item.description}</span><span className="mt-2 block font-mono text-[10px] uppercase text-primary-container">{item.technique === "boolean" ? "Measured geometry" : item.technique === "material" ? "Appearance only" : "Morphology reconstruction"}</span></button>)}</div>{preset && <div className="mt-5 grid gap-4 rounded-xl border border-outline-variant bg-surface-container-low p-4 sm:grid-cols-2"><label className="text-body-sm font-medium">Severity<select value={severity} onChange={(event) => setSeverity(event.target.value as CaseVariantRecipe["severity"])} className="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2"><option value="small">Small</option><option value="moderate">Moderate</option><option value="large">Large</option></select></label><label className="text-body-sm font-medium">Target surface<select value={targetSurface} onChange={(event) => setTargetSurface(event.target.value)} className="mt-1 block w-full rounded-lg border border-outline-variant bg-surface px-3 py-2"><option>occlusal</option><option>buccal</option><option>lingual</option><option>mesial</option><option>distal</option><option>incisal</option></select></label>{preset.caseId === "fracture" && <label className="text-body-sm font-medium">Fracture angle · {angleDeg}°<input type="range" min="10" max="75" value={angleDeg} onChange={(event) => setAngleDeg(Number(event.target.value))} className="mt-2 w-full" /></label>}{preset.technique === "boolean" && <label className="text-body-sm font-medium">Target depth · {depthMm.toFixed(1)} mm<input type="range" min="0.5" max="5" step="0.5" value={depthMm} onChange={(event) => setDepthMm(Number(event.target.value))} className="mt-2 w-full" /></label>}</div>}{preset?.requiresInternalAnatomy && <div className="mt-4 flex gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-body-sm text-amber-950"><ShieldCheck className="h-5 w-5 shrink-0" />This generated surface does not prove pulp or canal anatomy. The preset creates an external access opening only unless a segmented tissue model is attached.</div>}</main></div><footer className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant px-6 py-4"><p className="max-w-xl text-xs text-on-surface-variant">Next, mark or brush the target. Selecting this preset automatically fills the action and semantic instruction.</p><div className="flex gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button className="bg-primary-container text-on-primary" disabled={!preset} onClick={() => preset && onPrepare(preset, { presetId: preset.id, caseId: preset.caseId, technique: preset.technique, severity, angleDeg, depthMm, targetSurface, label: preset.label })}>Continue to mark region</Button></div></footer></div></div>;
}
