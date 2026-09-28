"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, Check, Download, Move3d, Rotate3d, RotateCcw, Scaling, Magnet, Share2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DEFAULT_JAW_PLACEMENT, jawPlacementWarnings, teethForArch, type JawArch, type JawPlacement } from "@/lib/jaw-placement";
import { cn } from "@/lib/utils";
import { JawPlacementCanvas, type PlacementTool } from "@/components/editor/jaw-placement-canvas";
import type { RemoteModelFormat } from "@/lib/model-format";

interface Props {
  open: boolean;
  initialPlacement?: JawPlacement | null;
  saving: boolean;
  onClose: () => void;
  onChange: (placement: JawPlacement) => void;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  originLabel: string;
  onExport: () => void;
  onPublish: () => void;
}

const AXES = ["Mesial / distal", "Buccal / lingual", "Occlusal / apical"];

export function JawPlacementDialog({ open, initialPlacement, saving, onClose, onChange, modelUrl, modelFormat, originLabel, onExport, onPublish }: Props) {
  const [placement, setPlacement] = useState(initialPlacement ?? DEFAULT_JAW_PLACEMENT);
  const [tool, setTool] = useState<PlacementTool>("translate");
  const teeth = useMemo(() => teethForArch(placement.arch), [placement.arch]);
  const alignmentWarnings = jawPlacementWarnings(placement);
  if (!open) return null;

  const update = (next: JawPlacement) => {
    setPlacement(next);
    onChange(next);
  };
  const selectArch = (arch: JawArch) => update({
    ...placement,
    arch,
    fdiTooth: arch === "upper" ? 16 : 46,
    templateId: `adult-standard-${arch}-v1`,
  });

  return <div className="fixed inset-0 z-[110] flex items-center justify-center bg-on-surface/65 p-4 backdrop-blur-sm">
    <div role="dialog" aria-modal="true" aria-labelledby="jaw-placement-title" className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-outline-variant bg-surface shadow-2xl">
      <header className="flex items-start justify-between border-b border-outline-variant px-6 py-4">
        <div><h2 id="jaw-placement-title" className="text-title-lg font-semibold">Place tooth in a jaw</h2><p className="mt-1 text-body-sm text-on-surface-variant">Choose the socket first, then refine position and orientation. Every change is autosaved.</p></div>
        <button type="button" onClick={onClose} className="rounded-full p-2 hover:bg-surface-container-high" aria-label="Close"><X className="h-5 w-5" /></button>
      </header>
      <div className="grid min-h-0 flex-1 lg:grid-cols-[1.35fr_0.8fr]">
        <section className="overflow-y-auto border-r border-outline-variant bg-surface-container-low p-6">
          <div className="mx-auto max-w-3xl rounded-2xl border border-outline-variant bg-surface p-5 shadow-sm">
            <div className="mb-5 flex justify-center gap-2">
              {(["lower", "upper"] as JawArch[]).map((arch) => <button key={arch} type="button" onClick={() => selectArch(arch)} className={cn("rounded-full px-4 py-2 text-sm font-semibold capitalize", placement.arch === arch ? "bg-primary-container text-on-primary" : "bg-surface-container hover:bg-surface-container-high")}>{arch} jaw</button>)}
            </div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              {([{ id: "translate", label: "Move", icon: Move3d }, { id: "rotate", label: "Rotate", icon: Rotate3d }, { id: "scale", label: "Resize tooth", icon: Scaling }] as const).map(({ id, label, icon: Icon }) => <button key={id} type="button" onClick={() => setTool(id)} className={cn("flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold", tool === id ? "border-primary-container bg-primary-container text-on-primary" : "border-outline-variant hover:border-primary-container")}><Icon className="h-4 w-4" />{label}</button>)}
              <button type="button" onClick={() => update({ ...placement, positionMm: [0, 0, 0], rotationDeg: [0, 0, 0], scale: 1 })} className="ml-auto flex items-center gap-1.5 rounded-lg border border-outline-variant px-3 py-2 text-xs font-semibold text-primary-container hover:border-primary-container"><Magnet className="h-4 w-4" />Snap to socket</button>
            </div>
            <JawPlacementCanvas placement={placement} tool={tool} modelUrl={modelUrl} modelFormat={modelFormat} onChange={update} />
            <p className="mb-3 text-center text-xs text-on-surface-variant">FDI tooth position · select the socket that will receive this tooth</p>
            <div className={cn("grid grid-cols-8 gap-2 rounded-[45%] border-2 border-outline-variant p-6", placement.arch === "upper" ? "border-b-0" : "border-t-0")}>
              {teeth.map((tooth) => <button key={tooth} type="button" onClick={() => update({ ...placement, fdiTooth: tooth })} className={cn("aspect-square rounded-lg border text-xs font-semibold transition", placement.fdiTooth === tooth ? "scale-110 border-primary-container bg-primary-container text-on-primary shadow-md" : "border-outline-variant bg-surface hover:border-primary-container")}>{tooth}</button>)}
            </div>
            <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950">Selected: FDI {placement.fdiTooth} on the {placement.arch === "lower" ? "mandible" : "maxilla"}. Automatic socket snapping is the starting pose; use the controls to verify contacts and occlusal alignment.</div>
          </div>
        </section>
        <aside className="overflow-y-auto p-6">
          <h3 className="font-semibold">Fine alignment</h3>
          <p className="mt-1 text-xs text-on-surface-variant">Values are relative to the template socket. Scale the tooth—not the jaw.</p>
          <div className="mt-5 space-y-5">
            {AXES.map((label, axis) => <label key={label} className="block text-sm font-medium">{label} · {placement.positionMm[axis].toFixed(1)} mm<input type="range" min="-5" max="5" step="0.1" value={placement.positionMm[axis]} onChange={(event) => { const value = [...placement.positionMm] as JawPlacement["positionMm"]; value[axis] = Number(event.target.value); update({ ...placement, positionMm: value }); }} className="mt-2 w-full" /></label>)}
            {AXES.map((label, axis) => <label key={`r-${label}`} className="block text-sm font-medium">Rotate {label.toLowerCase()} · {placement.rotationDeg[axis].toFixed(0)}°<input type="range" min="-30" max="30" step="1" value={placement.rotationDeg[axis]} onChange={(event) => { const value = [...placement.rotationDeg] as JawPlacement["rotationDeg"]; value[axis] = Number(event.target.value); update({ ...placement, rotationDeg: value }); }} className="mt-2 w-full" /></label>)}
            <label className="block text-sm font-medium">Tooth scale · {(placement.scale * 100).toFixed(0)}%<input type="range" min="0.7" max="1.3" step="0.01" value={placement.scale} onChange={(event) => update({ ...placement, scale: Number(event.target.value) })} className="mt-2 w-full" /></label>
          </div>
          <button type="button" onClick={() => update({ ...DEFAULT_JAW_PLACEMENT, arch: placement.arch, fdiTooth: placement.fdiTooth, templateId: placement.templateId })} className="mt-5 flex items-center gap-2 text-sm font-semibold text-primary-container"><RotateCcw className="h-4 w-4" />Reset fine alignment</button>
          {alignmentWarnings.length > 0 && <div className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950"><strong>Alignment review needed</strong><ul className="mt-2 list-disc space-y-1 pl-4">{alignmentWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
          <div className="mt-4 rounded-xl bg-surface-container-low p-4 text-xs text-on-surface-variant"><strong className="text-on-surface">Clinical check before export</strong><ul className="mt-2 list-disc space-y-1 pl-4"><li>Long axis follows the socket and neighbouring teeth.</li><li>Occlusal surface follows the arch plane.</li><li>No unintended overlap with adjacent teeth or gingiva.</li><li>Confirm real dimensions before simulator use.</li></ul></div>
        </aside>
      </div>
      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant px-6 py-4">
        <div><button type="button" onClick={onClose} className="flex items-center gap-2 text-sm font-semibold text-primary-container"><ArrowLeft className="h-4 w-4" />Back to {originLabel}</button><span className="mt-1 flex items-center gap-2 text-xs text-on-surface-variant">{saving ? <><span className="h-2 w-2 animate-pulse rounded-full bg-secondary" />Saving placement…</> : <><Check className="h-4 w-4 text-secondary" />All placement changes saved</>}</span></div>
        <div className="flex gap-2"><Button variant="outline" onClick={onPublish}><Share2 className="mr-2 h-4 w-4" />Publish</Button><Button onClick={onExport} className="bg-primary-container text-on-primary"><Download className="mr-2 h-4 w-4" />Export tooth in jaw</Button></div>
      </footer>
    </div>
  </div>;
}
