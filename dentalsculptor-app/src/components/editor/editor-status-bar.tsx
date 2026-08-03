"use client";

import { Mouse, Cpu, Globe } from "lucide-react";

export function EditorStatusBar() {
  const now = new Date().toISOString().replace("T", " ").slice(0, 19);

  return (
    <footer className="flex h-8 shrink-0 items-center justify-between bg-primary-container px-4 text-[10px] text-on-primary">
      <div className="flex items-center gap-6">
        <span className="hidden items-center gap-2 sm:flex">
          <Mouse className="h-3.5 w-3.5" />
          Left Click: Select · Right Click: Orbit · Alt+Click: Pan
        </span>
        <span className="hidden items-center gap-2 md:flex">
          <Cpu className="h-3.5 w-3.5" />
          GPU Usage: — · VRAM: —
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="hidden items-center gap-1 opacity-80 sm:flex">
          <Globe className="h-3.5 w-3.5" />
          Local Preview
        </span>
        <span className="text-label-mono">{now} UTC</span>
      </div>
    </footer>
  );
}
