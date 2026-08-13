"use client";

import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { GENERATION_COPY } from "@/lib/generation-copy";
import {
  ensureNotificationPermission,
  getNotifyOnGeneration,
  isNotificationSupported,
  setNotifyOnGeneration,
} from "@/lib/generation-notifications";
import { cn } from "@/lib/utils";

interface GenerationNotifyOptionProps {
  className?: string;
  disabled?: boolean;
}

/** Opt-in browser notification when a long-running 3D generation finishes. */
export function GenerationNotifyOption({ className, disabled }: GenerationNotifyOptionProps) {
  const [supported, setSupported] = useState(false);
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    setSupported(isNotificationSupported());
    setEnabled(getNotifyOnGeneration());
  }, []);

  if (!supported) return null;

  async function handleChange(checked: boolean) {
    setEnabled(checked);
    setNotifyOnGeneration(checked);
    if (checked) {
      const granted = await ensureNotificationPermission();
      if (!granted) {
        setEnabled(false);
        setNotifyOnGeneration(false);
      }
    }
  }

  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-2.5 rounded-lg border border-border-subtle bg-surface-container-low px-3 py-2.5 text-left",
        disabled && "pointer-events-none opacity-50",
        className
      )}
    >
      <Checkbox
        checked={enabled}
        disabled={disabled}
        onCheckedChange={(v) => handleChange(v === true)}
        className="mt-0.5 border-on-surface-variant/50"
      />
      <span className="text-body-sm leading-snug text-on-surface-variant">
        {GENERATION_COPY.notifyLabel}
      </span>
    </label>
  );
}
