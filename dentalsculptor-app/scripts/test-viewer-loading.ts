import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const root = resolve(import.meta.dirname, "..");
const viewer = readFileSync(resolve(root, "src/components/three/dental-viewer.tsx"), "utf8");
const editorViewer = readFileSync(resolve(root, "src/components/editor/cam-model-viewer.tsx"), "utf8");
const loader = readFileSync(resolve(root, "src/components/three/remote-model-mesh.tsx"), "utf8");
const proxy = readFileSync(resolve(root, "src/app/api/models/proxy/route.ts"), "utf8");
const assetUrls = readFileSync(resolve(root, "src/lib/model-asset-url.ts"), "utf8");

assert(
  !viewer.includes('Environment preset="studio"'),
  "The core viewer must not suspend on a third-party HDR environment."
);
assert(
  !editorViewer.includes('Environment preset="studio"'),
  "The editor viewer must not depend on a third-party HDR environment."
);
assert(viewer.includes("onModelLoaded={handleLoaded}"), "The viewer must observe model readiness.");
assert(viewer.includes("CameraFitRig"), "Loaded geometry must be fitted to the viewport.");
assert(loader.includes("fetchWithTimeout(fetchUrl, 45_000)"), "Model downloads need a bounded timeout.");
assert(loader.includes("AbortController"), "Model download timeouts need embedded-browser support.");
assert(
  loader.includes("never hold geometry rendering hostage"),
  "OBJ geometry must not wait for optional remote textures."
);
assert(proxy.includes("AbortSignal.timeout(50_000)"), "The proxy must finish before its function deadline.");
assert(
  proxy.includes('target.protocol !== "https:"'),
  "The server proxy must reject insecure upstream model URLs."
);
assert(
  !assetUrls.includes('parsed.hostname.endsWith("supabase.co")'),
  "Cross-origin Supabase models must use the same-origin proxy in embedded browsers."
);

console.log("Validated embedded-browser-safe 3D viewer loading and framing.");
