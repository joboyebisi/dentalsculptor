"use client";

import { Suspense, useState, useCallback } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { Button } from "@/components/ui/button";
import { Glasses, Monitor } from "lucide-react";

function XRPreviewScene() {
  return (
    <>
      <PerspectiveCamera makeDefault position={[2, 1.5, 2.5]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 8, 5]} intensity={1.2} />
      <mesh position={[0, 0.5, 0]} castShadow>
        <cylinderGeometry args={[0.5, 0.35, 1.8, 32]} />
        <meshStandardMaterial color="#f5e6d3" roughness={0.4} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.4, 0]}>
        <planeGeometry args={[6, 6]} />
        <meshStandardMaterial color="#E2E8F0" />
      </mesh>
      <OrbitControls target={[0, 0.5, 0]} />
    </>
  );
}

export function WebXRViewer({
  className = "h-full w-full",
  projectTitle,
  onLaunch,
}: {
  className?: string;
  projectTitle?: string;
  onLaunch?: () => void;
}) {
  const [xrSupported, setXrSupported] = useState<boolean | null>(null);
  const [launching, setLaunching] = useState(false);

  const checkXRSupport = useCallback(async () => {
    if (typeof navigator !== "undefined" && "xr" in navigator) {
      try {
        const supported = await (navigator as any).xr.isSessionSupported("immersive-vr");
        setXrSupported(supported);
        return supported;
      } catch {
        setXrSupported(false);
        return false;
      }
    }
    setXrSupported(false);
    return false;
  }, []);

  const launchXR = useCallback(async () => {
    setLaunching(true);
    onLaunch?.();

    const supported = xrSupported ?? (await checkXRSupport());

    if (supported && (navigator as any).xr) {
      try {
        const canvas = document.querySelector("canvas");
        if (canvas) {
          const session = await (navigator as any).xr.requestSession("immersive-vr", {
            optionalFeatures: ["hand-tracking", "local-floor"],
          });
          await (canvas as any).getContext("webgl2")?.makeXRCompatible?.();
          // WebXR session started — full integration requires XR render loop
          session.addEventListener("end", () => setLaunching(false));
        }
      } catch (err) {
        console.warn("WebXR session failed:", err);
      }
    }
    setLaunching(false);
  }, [xrSupported, checkXRSupport, onLaunch]);

  return (
    <div className={`relative flex flex-col ${className}`}>
      <div className="flex items-center justify-between border-b border-border-subtle bg-panel-bg px-4 py-3">
        <div>
          <h2 className="text-headline-md font-semibold">{projectTitle ?? "XR Preview"}</h2>
          <p className="text-body-sm text-on-surface-variant">
            Desktop preview → WebXR → Meta Quest experience
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={checkXRSupport}>
            <Monitor className="mr-2 h-4 w-4" />
            Check XR Support
          </Button>
          <Button size="sm" onClick={launchXR} disabled={launching}>
            <Glasses className="mr-2 h-4 w-4" />
            {launching ? "Launching..." : "Launch in Meta Quest"}
          </Button>
        </div>
      </div>

      <div className="relative flex-1 bg-surface-container-low">
        <Canvas>
          <Suspense fallback={null}>
            <XRPreviewScene />
          </Suspense>
        </Canvas>

        {xrSupported === false && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
            <div className="glass-panel max-w-md rounded-xl p-6 text-center">
              <Glasses className="mx-auto mb-3 h-10 w-10 text-primary-container" />
              <h3 className="mb-2 text-headline-md font-semibold">Meta Quest Required</h3>
              <p className="text-body-sm text-on-surface-variant">
                Open this URL in the Meta Quest Browser to launch the immersive experience.
                Hand tracking and controller navigation are supported.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
