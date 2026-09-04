"use client";

import { useCallback, useEffect, useState } from "react";

type DiscoveredTool = {
  name: string;
  description?: string;
};

type ModelContextApi = {
  getTools: () => Promise<DiscoveredTool[]>;
};

function getModelContext(): ModelContextApi | undefined {
  return (document as Document & { modelContext?: ModelContextApi }).modelContext;
}

export function WebMcpDiagnostics() {
  const [supported, setSupported] = useState<boolean | null>(null);
  const [tools, setTools] = useState<DiscoveredTool[]>([]);
  const [error, setError] = useState<string | null>(null);

  const inspect = useCallback(async () => {
    const modelContext = getModelContext();
    setSupported(Boolean(modelContext));
    setError(null);
    if (!modelContext) {
      setTools([]);
      return;
    }
    try {
      setTools(await modelContext.getTools());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Tool discovery failed.");
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void inspect(), 0);
    const lateInjection = window.setTimeout(() => void inspect(), 750);
    return () => {
      window.clearTimeout(initial);
      window.clearTimeout(lateInjection);
    };
  }, [inspect]);

  return (
    <section className="rounded-xl border border-border-subtle bg-panel-bg p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-headline-md font-semibold text-text-main">Live WebMCP diagnostics</h2>
          <p className="mt-1 text-body-sm text-on-surface-variant">
            This reads the browser&apos;s tool registry; it does not simulate registration.
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            supported ? "bg-emerald-100 text-emerald-800" : "bg-surface-container-low text-on-surface-variant"
          }`}
        >
          {supported === null ? "Checking…" : supported ? "WebMCP available" : "WebMCP unavailable"}
        </span>
      </div>

      {!supported && supported !== null && (
        <p className="mt-5 rounded-lg bg-surface-container-low p-4 text-body-sm text-on-surface-variant">
          Open this page in ChatGPT&apos;s in-app browser, or enable{" "}
          <code>chrome://flags/#enable-webmcp-testing</code> in Chrome 149+.
        </p>
      )}

      {error && <p className="mt-5 text-body-sm text-error">{error}</p>}

      {supported && (
        <div className="mt-5">
          <p className="text-sm font-medium text-text-main">
            {tools.length} tool{tools.length === 1 ? "" : "s"} registered on this page
          </p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {tools.map((tool) => (
              <li key={tool.name} className="rounded-lg border border-border-subtle p-3">
                <code className="text-xs font-semibold text-primary-container">{tool.name}</code>
                {tool.description && (
                  <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">
                    {tool.description}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={() => void inspect()}
        className="mt-5 rounded-lg border border-border-subtle px-4 py-2 text-sm font-medium text-text-main hover:bg-surface-container-low"
      >
        Refresh tool discovery
      </button>
    </section>
  );
}
