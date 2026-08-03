export function PreviewBanner() {
  if (process.env.UI_PREVIEW_MODE !== "true") return null;

  return (
    <div className="fixed bottom-4 left-1/2 z-[100] -translate-x-1/2 rounded-full border border-warning/30 bg-warning/10 px-4 py-2 text-body-sm text-text-main shadow-sm backdrop-blur-sm">
      UI Preview Mode — Clerk &amp; database bypassed. Set <code className="text-label-mono">UI_PREVIEW_MODE=false</code> for full auth.
    </div>
  );
}
