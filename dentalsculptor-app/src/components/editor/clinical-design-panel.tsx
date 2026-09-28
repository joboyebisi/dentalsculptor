"use client";

import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Eye, MousePointer2, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CaseVariantRecipe } from "@/lib/case-variant-recipes";
import { cn } from "@/lib/utils";

const SITE_POINTS: Record<string, { x: number; y: number; label: string }> = {
  "central-fossa": { x: 50, y: 52, label: "Central fossa" },
  "mesial-pit": { x: 33, y: 50, label: "Mesial pit" },
  "distal-pit": { x: 67, y: 50, label: "Distal pit" },
  "buccal-pit": { x: 50, y: 72, label: "Buccal pit" },
  "lingual-pit": { x: 50, y: 30, label: "Lingual pit" },
};

const CUSP_POINTS: Record<string, { x: number; y: number; label: string }> = {
  mesiobuccal: { x: 29, y: 70, label: "MB" },
  distobuccal: { x: 70, y: 70, label: "DB" },
  mesiolingual: { x: 29, y: 28, label: "ML" },
  distolingual: { x: 70, y: 28, label: "DL" },
  palatal: { x: 50, y: 25, label: "P" },
};

export function ClinicalDesignPanel({ open, onToggle, recipe, onChange, onPlaceTarget, onPreview, previewLoading, targetReady, snapFeedback }: {
  open: boolean;
  onToggle: () => void;
  recipe: CaseVariantRecipe;
  onChange: (recipe: CaseVariantRecipe) => void;
  onPlaceTarget: (site: string) => void;
  onPreview: () => void;
  previewLoading: boolean;
  targetReady: boolean;
  snapFeedback?: { confidence: number; sampleCount: number } | null;
}) {
  const isFracture = recipe.caseId === "fracture";
  const points = isFracture ? CUSP_POINTS : SITE_POINTS;
  const selected = isFracture ? recipe.namedCusp : recipe.targetSite;
  const update = (patch: Partial<CaseVariantRecipe>) => onChange({ ...recipe, ...patch });

  if (!open) return <button type="button" onClick={onToggle} className="flex h-full w-10 shrink-0 flex-col items-center gap-2 border-l border-outline-variant py-4 text-on-surface-variant hover:bg-surface-container-low" title="Open case design"><ChevronLeft className="h-4 w-4" /><SlidersHorizontal className="h-4 w-4" /></button>;

  return <aside className="editor-chrome-panel editor-scrollbar flex h-full w-[300px] shrink-0 flex-col overflow-hidden border-l border-outline-variant">
    <header className="flex items-center justify-between border-b border-outline-variant px-4 py-3"><div className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4 text-primary-container" /><span className="text-label-caps font-bold">Case design</span></div><button type="button" onClick={onToggle} className="rounded p-1 hover:bg-surface-container"><ChevronRight className="h-4 w-4" /></button></header>
    <div className="editor-scrollbar flex-1 space-y-5 overflow-y-auto p-4">
      <section><p className="text-xs font-semibold">1. Choose the anatomical target</p><p className="mt-1 text-[11px] text-on-surface-variant">Occlusal view · select a landmark, then place its marker on the real model.</p>
        <div className="relative mx-auto mt-3 aspect-square w-48 rounded-[42%] border-2 border-outline-variant bg-[#f3edda] shadow-inner">
          <div className="absolute left-1/2 top-[18%] h-[64%] w-px -translate-x-1/2 rotate-12 bg-amber-800/25" /><div className="absolute left-[22%] top-1/2 h-px w-[56%] -translate-y-1/2 bg-amber-800/20" />
          {Object.entries(points).map(([id, point]) => <button key={id} type="button" onClick={() => { update(isFracture ? { namedCusp: id } : { targetSite: id }); onPlaceTarget(id); }} className={cn("absolute flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border text-[9px] font-bold shadow-sm", selected === id ? "border-primary-container bg-primary-container text-on-primary ring-4 ring-primary-container/20" : "border-outline-variant bg-white hover:border-primary-container")} style={{ left: `${point.x}%`, top: `${point.y}%` }} title={point.label}>{point.label.split(" ").map((word) => word[0]).join("")}</button>)}
        </div>
      </section>

      {!isFracture && <section className="grid grid-cols-2 gap-3"><label className="text-xs font-semibold">Sites<select value={recipe.lesionCount ?? 1} onChange={(e) => update({ lesionCount: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-2 py-2"><option value={1}>1</option><option value={2}>2</option><option value={3}>3</option></select></label><label className="text-xs font-semibold">Severity<select value={recipe.severity} onChange={(e) => update({ severity: e.target.value as CaseVariantRecipe["severity"] })} className="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-2 py-2"><option value="small">Small</option><option value="moderate">Moderate</option><option value="large">Large</option></select></label></section>}
      {!isFracture && <label className="block text-xs font-semibold">Surface coverage · {recipe.coveragePercent ?? 15}%<input type="range" min="2" max="60" value={recipe.coveragePercent ?? 15} onChange={(e) => update({ coveragePercent: Number(e.target.value) })} className="mt-2 w-full" /><span className="flex justify-between text-[9px] text-on-surface-variant"><span>Conservative</span><span>Extensive</span></span></label>}
      {isFracture && <label className="block text-xs font-semibold">Fracture angle · {recipe.angleDeg}°<input type="range" min="10" max="75" value={recipe.angleDeg} onChange={(e) => update({ angleDeg: Number(e.target.value) })} className="mt-2 w-full" /></label>}
      <label className="block text-xs font-semibold">Depth · {recipe.depthMm.toFixed(1)} mm<input type="range" min="0.5" max="5" step="0.5" value={recipe.depthMm} onChange={(e) => update({ depthMm: Number(e.target.value) })} className="mt-2 w-full" /></label>
      <label className="block text-xs font-semibold">Target surface<select value={recipe.targetSurface} onChange={(e) => update({ targetSurface: e.target.value })} className="mt-1 w-full rounded-lg border border-outline-variant bg-surface px-2 py-2"><option value="occlusal">Occlusal</option><option value="buccal">Buccal</option><option value="lingual">Lingual</option><option value="mesial">Mesial</option><option value="distal">Distal</option></select></label>

      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-[11px] text-blue-950"><MousePointer2 className="mb-1 h-4 w-4" />{snapFeedback ? <>Snapped to the visible mesh surface with <strong>{Math.round(snapFeedback.confidence * 100)}% confidence</strong> from {snapFeedback.sampleCount} surface samples. You can still adjust it.</> : <>Choose a landmark to analyse and snap to the visible tooth surface.</>}</div>
      {recipe.depthMm > 2 || (recipe.coveragePercent ?? 0) > 35 ? <div className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-[11px] text-amber-950"><AlertTriangle className="h-4 w-4 shrink-0" />This is an extensive case. Confirm remaining cusp and ridge strength.</div> : <div className="flex gap-2 rounded-lg bg-emerald-50 p-3 text-[11px] text-emerald-950"><CheckCircle2 className="h-4 w-4 shrink-0" />Parameters are within the conservative authoring range.</div>}
    </div>
    <footer className="border-t border-outline-variant p-4"><Button className="w-full bg-primary-container text-on-primary" disabled={!targetReady || previewLoading} onClick={onPreview}><Eye className="mr-2 h-4 w-4" />{previewLoading ? "Rendering preview…" : targetReady ? "Preview planned result" : "Place target to preview"}</Button></footer>
  </aside>;
}
