"use client";

import Link from "next/link";
import { Menu, Eye, Share2, Download, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppLogoMark } from "@/components/brand/app-logo";
import { projectFileName } from "@/lib/editor-segmentation";
import { cn } from "@/lib/utils";

export type EditorTab = "authoring" | "history" | "drafts";

interface EditorHeaderProps {
  projectTitle: string;
  projectStatus: string;
  activeTab: EditorTab;
  onTabChange: (tab: EditorTab) => void;
  draftCount?: number;
  saving?: boolean;
  exporting?: boolean;
  exportDisabled?: boolean;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onSave?: () => void;
  onExport?: () => void;
}

const TABS: { id: EditorTab; label: string }[] = [
  { id: "authoring", label: "Authoring" },
  { id: "history", label: "Version History" },
  { id: "drafts", label: "Drafts" },
];

export function EditorHeader({
  projectTitle,
  projectStatus,
  activeTab,
  onTabChange,
  draftCount = 0,
  saving,
  exporting,
  exportDisabled,
  sidebarOpen,
  onToggleSidebar,
  onSave,
  onExport,
}: EditorHeaderProps) {
  const fileName = projectFileName(projectTitle);

  return (
    <header className="z-40 flex h-14 shrink-0 items-center justify-between border-b border-outline-variant bg-panel-bg px-4 md:px-5">
      <div className="flex min-w-0 flex-1 items-center gap-3 md:gap-5">
        <div className="flex shrink-0 items-center gap-2.5">
          <button
            type="button"
            onClick={onToggleSidebar}
            className="rounded-lg p-2 text-on-surface transition-colors hover:bg-surface-container"
            aria-label={sidebarOpen ? "Close dashboard menu" : "Open dashboard menu"}
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link href="/dashboard" className="hidden items-center gap-2 sm:flex">
            <AppLogoMark size="xs" />
            <span className="text-body-md font-bold text-primary-container">DentalSculptor</span>
          </Link>
        </div>

        <div className="hidden h-5 w-px shrink-0 bg-outline-variant sm:block" />

        <div className="flex min-w-0 flex-1 items-center gap-3 md:gap-5">
          <div className="flex min-w-0 items-center gap-2 rounded-md border border-outline-variant bg-surface-container-low px-2.5 py-1.5">
            <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-secondary" />
            <span className="truncate font-mono text-body-sm font-medium text-on-surface" title={fileName}>
              {fileName}
            </span>
            <span className="hidden shrink-0 rounded bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant md:inline">
              {projectStatus}
            </span>
          </div>

          <nav className="hidden items-stretch gap-1 lg:flex">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => onTabChange(tab.id)}
                className={cn(
                  "relative px-3 py-1.5 text-body-sm font-medium transition-colors",
                  activeTab === tab.id
                    ? "text-primary-container after:absolute after:inset-x-3 after:-bottom-[13px] after:h-0.5 after:rounded-full after:bg-primary-container"
                    : "text-on-surface-variant hover:text-on-surface"
                )}
              >
                {tab.label}
                {tab.id === "drafts" && draftCount > 0 && (
                  <span className="ml-1.5 rounded-full bg-surface-container px-1.5 py-0.5 text-[10px] font-semibold text-on-surface-variant">
                    {draftCount}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 md:gap-2">
        {onSave && (
          <Button variant="ghost" size="sm" onClick={onSave} disabled={saving} className="hidden sm:inline-flex">
            <Save className="mr-1.5 h-4 w-4" />
            {saving ? "Saving…" : "Save"}
          </Button>
        )}
        <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
          <Eye className="mr-1.5 h-4 w-4" />
          Preview
        </Button>
        <Button variant="ghost" size="sm" className="hidden md:inline-flex">
          <Share2 className="mr-1.5 h-4 w-4" />
          Share
        </Button>
        <Button
          size="sm"
          className="bg-primary-container text-on-primary shadow-sm"
          onClick={onExport}
          disabled={exportDisabled || exporting}
        >
          <Download className="mr-1.5 h-4 w-4" />
          {exporting ? "Exporting…" : "Export"}
        </Button>
      </div>
    </header>
  );
}
