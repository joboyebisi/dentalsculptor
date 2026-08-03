"use client";

import { useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { trackEvent } from "@/lib/posthog";
import type { ResearchEventType } from "@/generated/prisma/client";

export function useResearchTracker(userId?: string) {
  const sessionId = useRef(uuidv4());

  const track = useCallback(
    async (
      eventType: ResearchEventType,
      projectId?: string,
      metadata?: Record<string, unknown>
    ) => {
      trackEvent(eventType, { projectId, ...metadata });

      if (!userId) return;

      try {
        await fetch("/api/research/events", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            eventType,
            projectId,
            metadata,
            sessionId: sessionId.current,
          }),
        });
      } catch (error) {
        console.error("Failed to track event:", error);
      }
    },
    [userId]
  );

  return { track, sessionId: sessionId.current };
}
