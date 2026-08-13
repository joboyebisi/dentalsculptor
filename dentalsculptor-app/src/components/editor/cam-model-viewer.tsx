"use client";

import { useRef, useMemo, useCallback, useEffect, useState, forwardRef, useImperativeHandle } from "react";
import { Loader2 } from "lucide-react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line, Grid, Environment } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import type { GeneratedMesh } from "@/lib/model-generator";
import type { SegmentPart } from "@/lib/editor-segmentation";
import { VIEWPORT_THEME, EDITOR_SURFACE } from "@/lib/constants";
import {
  CAMERA,
  computeDefaultCameraPosition,
  computeDefaultPerspectiveCameraFrustum,
  type Coordinate,
} from "@/lib/camera-utils";
import { RemoteModelMesh } from "@/components/three/remote-model-mesh";
import type { RemoteModelFormat } from "@/lib/model-format";

export interface RectMark {
  id: string;
  text: string;
  color: string;
  x: number;
  y: number;
  width: number;
  height: number;
  corners3d?: [number, number, number][];
}

export interface CamViewerHandle {
  resetHome: () => void;
  raycastAt: (clientX: number, clientY: number) => THREE.Vector3 | null;
}

export type ModelLoadStatus = "none" | "loading" | "ready" | "error";

interface CamModelViewerProps {
  meshData?: GeneratedMesh | null;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  mtlUrl?: string | null;
  sourcePreview?: string | null;
  wireframe?: boolean;
  rectMarks?: RectMark[];
  markMode?: boolean;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  onRectMarkComplete?: (mark: Omit<RectMark, "id" | "text">) => void;
  segmentParts?: SegmentPart[];
  activePartId?: string | null;
  modelSelected?: boolean;
  className?: string;
  onModelStatusChange?: (status: ModelLoadStatus, detail?: string) => void;
}

function computeRemoteModelVisuals(
  segmentParts: SegmentPart[],
  activePartId: string | null | undefined,
  modelSelected: boolean
) {
  const allHidden = segmentParts.length > 0 && segmentParts.every((p) => !p.visible);
  const active = segmentParts.find((p) => p.id === activePartId);
  const highlighted = Boolean(active || modelSelected);
  return {
    opacity: allHidden ? 0.2 : 1,
    emissiveHex: active?.color ?? VIEWPORT_THEME.selectEmissive,
    emissiveIntensity: highlighted ? 0.28 : 0,
    highlighted,
  };
}

function computeSelectionVisuals(
  segmentParts: SegmentPart[],
  activePartId: string | null | undefined,
  modelSelected: boolean
) {
  const visible = segmentParts.filter((p) => p.visible);
  const total = Math.max(segmentParts.length, 1);
  const ratio = visible.length / total;
  const opacity =
    segmentParts.length > 0 && visible.length === 0 ? 0.12 : 0.45 + 0.55 * ratio;
  const active = segmentParts.find((p) => p.id === activePartId);
  const highlighted = Boolean(active || modelSelected);
  return {
    opacity,
    emissiveHex: active?.color ?? VIEWPORT_THEME.selectEmissive,
    emissiveIntensity: highlighted ? 0.32 : 0,
    highlighted,
  };
}

function applyMeshSelection(
  root: THREE.Object3D,
  visuals: ReturnType<typeof computeSelectionVisuals>,
  wireframe?: boolean
) {
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach((mat) => {
      if (mat instanceof THREE.MeshPhongMaterial || mat instanceof THREE.MeshStandardMaterial || mat instanceof THREE.MeshLambertMaterial) {
        mat.transparent = visuals.opacity < 1;
        mat.opacity = visuals.opacity;
        if ("emissive" in mat) {
          mat.emissive = new THREE.Color(visuals.emissiveHex);
          mat.emissiveIntensity = visuals.emissiveIntensity;
        }
        if ("wireframe" in mat) mat.wireframe = Boolean(wireframe);
      }
    });
  });
}

function buildGeometry(meshData?: GeneratedMesh | null) {
  if (meshData?.vertices?.length) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(meshData.vertices, 3));
    if (meshData.normals?.length) {
      geo.setAttribute("normal", new THREE.Float32BufferAttribute(meshData.normals, 3));
    } else {
      geo.computeVertexNormals();
    }
    if (meshData.indices?.length) geo.setIndex(meshData.indices);
    return geo;
  }
  return new THREE.CylinderGeometry(0.5, 0.35, 1.8, 32, 8, false);
}

function RemoteModelGroup({
  url,
  modelFormat,
  mtlUrl,
  wireframe,
  meshGroupRef,
  selectMode,
  onMeshSelect,
  segmentParts,
  activePartId,
  modelSelected,
  onModelLoaded,
  onModelError,
}: {
  url: string;
  modelFormat?: RemoteModelFormat | string | null;
  mtlUrl?: string | null;
  wireframe?: boolean;
  meshGroupRef: React.RefObject<THREE.Group | null>;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  segmentParts: SegmentPart[];
  activePartId?: string | null;
  modelSelected?: boolean;
  onModelLoaded?: (info: { meshCount: number }) => void;
  onModelError?: (message: string) => void;
}) {
  const modelRootRef = useRef<THREE.Object3D | null>(null);
  const visuals = useMemo(
    () => computeRemoteModelVisuals(segmentParts, activePartId, Boolean(modelSelected)),
    [segmentParts, activePartId, modelSelected]
  );

  const handleClone = useCallback((root: THREE.Object3D) => {
    modelRootRef.current = root;
  }, []);

  const handleLoaded = useCallback(
    (info: { meshCount: number }) => {
      onModelLoaded?.(info);
    },
    [onModelLoaded]
  );

  useEffect(() => {
    if (modelRootRef.current) {
      applyMeshSelection(modelRootRef.current, visuals, wireframe);
    }
  }, [visuals, wireframe]);

  return (
    <group
      ref={meshGroupRef}
      onClick={(e) => {
        if (selectMode) {
          e.stopPropagation();
          onMeshSelect?.();
        }
      }}
    >
      <RemoteModelMesh
        url={url}
        format={modelFormat}
        mtlUrl={mtlUrl}
        wireframe={wireframe}
        onClone={handleClone}
        onLoaded={handleLoaded}
        onError={onModelError}
      />
    </group>
  );
}

function MeshGroup({
  meshData,
  wireframe,
  meshGroupRef,
  selectMode,
  onMeshSelect,
  segmentParts,
  activePartId,
  modelSelected,
}: {
  meshData?: GeneratedMesh | null;
  wireframe?: boolean;
  meshGroupRef: React.RefObject<THREE.Group | null>;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  segmentParts: SegmentPart[];
  activePartId?: string | null;
  modelSelected?: boolean;
}) {
  const geometry = useMemo(() => buildGeometry(meshData), [meshData]);
  const visuals = useMemo(
    () => computeSelectionVisuals(segmentParts, activePartId, Boolean(modelSelected)),
    [segmentParts, activePartId, modelSelected]
  );

  return (
    <group ref={meshGroupRef}>
      <mesh
        geometry={geometry}
        castShadow
        receiveShadow
        onClick={(e) => {
          if (selectMode) {
            e.stopPropagation();
            onMeshSelect?.();
          }
        }}
      >
        <meshPhongMaterial
          color={VIEWPORT_THEME.meshDefault}
          specular="#ffffff"
          shininess={24}
          wireframe={wireframe}
          side={THREE.DoubleSide}
          transparent={visuals.opacity < 1}
          opacity={visuals.opacity}
          emissive={visuals.emissiveHex}
          emissiveIntensity={visuals.emissiveIntensity}
        />
      </mesh>
    </group>
  );
}

function RectMark3D({ mark }: { mark: RectMark }) {
  if (!mark.corners3d || mark.corners3d.length < 4) return null;
  const pts = mark.corners3d.map((c) => new THREE.Vector3(...c));
  const closed = [...pts, pts[0]!];
  return <Line points={closed} color={mark.color} lineWidth={2} />;
}

function CameraRig({
  meshGroupRef,
  controlsRef,
  onReady,
  fitGeneration = 0,
}: {
  meshGroupRef: React.RefObject<THREE.Group | null>;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onReady: (home: { position: Coordinate; target: Coordinate }) => void;
  fitGeneration?: number;
}) {
  const { camera, size } = useThree();

  const fitCamera = useCallback(() => {
    if (!meshGroupRef.current) return;
    const box = new THREE.Box3().setFromObject(meshGroupRef.current);
    if (box.isEmpty()) return;

    const center = box.getCenter(new THREE.Vector3());
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const objectCenter: Coordinate = { x: center.x, y: center.y, z: center.z };
    const r = sphere.radius || 1;

    const { position, distance } = computeDefaultCameraPosition(
      CAMERA.PHI_FOV,
      r,
      objectCenter,
      CAMERA.HOME_AZIMUTH,
      CAMERA.HOME_ELEVATION,
      CAMERA.ZOOM_SCALAR
    );

    const frustum = computeDefaultPerspectiveCameraFrustum(r, distance);

    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov = CAMERA.PHI_FOV;
      camera.aspect = size.width / size.height;
      camera.near = frustum.near;
      camera.far = frustum.far;
      camera.position.set(position.x, position.y, position.z);
      camera.updateProjectionMatrix();
    }

    controlsRef.current?.target.set(objectCenter.x, objectCenter.y, objectCenter.z);
    controlsRef.current?.update();
    onReady({ position, target: objectCenter });
  }, [camera, size, meshGroupRef, controlsRef, onReady]);

  useEffect(() => {
    const t = setTimeout(fitCamera, fitGeneration > 0 ? 0 : 50);
    return () => clearTimeout(t);
  }, [fitCamera, fitGeneration]);

  useEffect(() => {
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.aspect = size.width / size.height;
      camera.updateProjectionMatrix();
    }
  }, [size, camera]);

  return null;
}

function SceneContent({
  meshData,
  modelUrl,
  modelFormat,
  mtlUrl,
  wireframe,
  rectMarks,
  meshGroupRef,
  controlsRef,
  markMode,
  selectMode,
  onMeshSelect,
  onHomeReady,
  segmentParts,
  activePartId,
  modelSelected,
  fitGeneration,
  onModelLoaded,
  onModelError,
}: {
  meshData?: GeneratedMesh | null;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  mtlUrl?: string | null;
  wireframe?: boolean;
  rectMarks?: RectMark[];
  meshGroupRef: React.RefObject<THREE.Group | null>;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  markMode?: boolean;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  onHomeReady: (home: { position: Coordinate; target: Coordinate }) => void;
  segmentParts: SegmentPart[];
  activePartId?: string | null;
  modelSelected?: boolean;
  fitGeneration?: number;
  onModelLoaded?: (info: { meshCount: number }) => void;
  onModelError?: (message: string) => void;
}) {
  return (
    <>
      <color attach="background" args={[VIEWPORT_THEME.background]} />
      <Environment preset="studio" environmentIntensity={0.55} />
      <ambientLight intensity={0.65} />
      <hemisphereLight args={["#ffffff", "#d1d5db", 0.55]} />
      <directionalLight position={[8, 10, 6]} intensity={1.2} castShadow />
      <directionalLight position={[-5, 3, -4]} intensity={0.5} />
      <Grid
        args={[10, 10]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor="#D1D5DB"
        sectionSize={2}
        sectionThickness={1}
        sectionColor="#9CA3AF"
        fadeDistance={14}
        position={[0, -0.01, 0]}
      />

      {modelUrl ? (
          <RemoteModelGroup
            url={modelUrl}
            modelFormat={modelFormat}
            mtlUrl={mtlUrl}
            wireframe={wireframe}
            meshGroupRef={meshGroupRef}
            selectMode={selectMode}
            onMeshSelect={onMeshSelect}
            segmentParts={segmentParts}
            activePartId={activePartId}
            modelSelected={modelSelected}
            onModelLoaded={onModelLoaded}
            onModelError={onModelError}
          />
      ) : (
        <MeshGroup
          meshData={meshData}
          wireframe={wireframe}
          meshGroupRef={meshGroupRef}
          selectMode={selectMode}
          onMeshSelect={onMeshSelect}
          segmentParts={segmentParts}
          activePartId={activePartId}
          modelSelected={modelSelected}
        />
      )}

      {rectMarks?.map((m) => (
        <RectMark3D key={m.id} mark={m} />
      ))}

      <OrbitControls
        ref={controlsRef}
        makeDefault
        enableDamping
        dampingFactor={CAMERA.CONTROL_DAMPING}
        screenSpacePanning
        enabled={!markMode}
        minDistance={0.5}
        maxDistance={50}
      />

      <CameraRig
        meshGroupRef={meshGroupRef}
        controlsRef={controlsRef}
        onReady={onHomeReady}
        fitGeneration={fitGeneration}
      />
    </>
  );
}

function RaycastBridge({
  meshGroupRef,
  raycastRef,
}: {
  meshGroupRef: React.RefObject<THREE.Group | null>;
  raycastRef: React.MutableRefObject<(x: number, y: number) => THREE.Vector3 | null>;
}) {
  const { camera, gl } = useThree();
  raycastRef.current = (clientX: number, clientY: number) => {
    if (!meshGroupRef.current) return null;
    const rect = gl.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObject(meshGroupRef.current, true);
    return hits[0]?.point ?? null;
  };
  return null;
}

export const CamModelViewer = forwardRef<CamViewerHandle, CamModelViewerProps>(function CamModelViewer(
  {
    meshData,
    modelUrl,
    modelFormat,
    mtlUrl,
    sourcePreview,
    wireframe,
    rectMarks,
    markMode,
    selectMode,
    onMeshSelect,
    onRectMarkComplete,
    segmentParts = [],
    activePartId = null,
    modelSelected = false,
    className = "h-full w-full",
    onModelStatusChange,
  },
  ref
) {
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const raycastRef = useRef<(x: number, y: number) => THREE.Vector3 | null>(() => null);
  const homeRef = useRef<{ position: Coordinate; target: Coordinate } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [drawing, setDrawing] = useState<{ startX: number; startY: number; curX: number; curY: number } | null>(null);
  const [fitGeneration, setFitGeneration] = useState(0);
  const [modelLoadStatus, setModelLoadStatus] = useState<ModelLoadStatus>(
    modelUrl || meshData?.vertices?.length ? "loading" : "none"
  );
  const [modelLoadDetail, setModelLoadDetail] = useState<string | undefined>();
  const statusCallbackRef = useRef(onModelStatusChange);
  statusCallbackRef.current = onModelStatusChange;
  const modelSourceKeyRef = useRef<string | null>(null);

  const hasMesh = Boolean(meshData?.vertices?.length) || Boolean(modelUrl);

  useEffect(() => {
    const sourceKey = modelUrl ?? (meshData?.vertices?.length ? "__meshData__" : null);
    if (!sourceKey) {
      modelSourceKeyRef.current = null;
      setModelLoadStatus("none");
      statusCallbackRef.current?.("none");
      return;
    }
    if (modelSourceKeyRef.current !== sourceKey) {
      modelSourceKeyRef.current = sourceKey;
      setModelLoadStatus("loading");
      statusCallbackRef.current?.("loading");
    }
  }, [modelUrl, meshData]);

  useEffect(() => {
    if (modelLoadStatus !== "loading" || !hasMesh) return;
    const timeout = setTimeout(() => {
      const msg = "Load timed out — try Generate Model again";
      setModelLoadStatus("error");
      setModelLoadDetail(msg);
      statusCallbackRef.current?.("error", msg);
    }, 60_000);
    return () => clearTimeout(timeout);
  }, [modelLoadStatus, hasMesh, modelUrl]);

  const handleModelLoaded = useCallback(
    (info: { meshCount: number }) => {
      if (info.meshCount === 0) {
        const msg = "Model file loaded but contains no geometry";
        setModelLoadStatus("error");
        setModelLoadDetail(msg);
        onModelStatusChange?.("error", msg);
        return;
      }
      setFitGeneration((g) => g + 1);
      setModelLoadStatus("ready");
      setModelLoadDetail(`${info.meshCount} mesh${info.meshCount === 1 ? "" : "es"}`);
      onModelStatusChange?.("ready", `${info.meshCount} mesh${info.meshCount === 1 ? "" : "es"}`);
    },
    [onModelStatusChange]
  );

  const handleModelError = useCallback(
    (message: string) => {
      setModelLoadStatus("error");
      setModelLoadDetail(message);
      onModelStatusChange?.("error", message);
    },
    [onModelStatusChange]
  );

  useEffect(() => {
    if (meshData?.vertices?.length && !modelUrl) {
      setFitGeneration((g) => g + 1);
      setModelLoadStatus("ready");
      onModelStatusChange?.("ready", "procedural mesh");
    }
  }, [meshData, modelUrl, onModelStatusChange]);

  useImperativeHandle(ref, () => ({
    resetHome: () => {
      const home = homeRef.current;
      if (!home || !controlsRef.current) return;
      const cam = controlsRef.current.object;
      cam.position.set(home.position.x, home.position.y, home.position.z);
      controlsRef.current.target.set(home.target.x, home.target.y, home.target.z);
      controlsRef.current.update();
    },
    raycastAt: (clientX, clientY) => raycastRef.current(clientX, clientY),
  }));

  const handleHomeReady = useCallback((home: { position: Coordinate; target: Coordinate }) => {
    homeRef.current = home;
  }, []);

  const normRect = (startX: number, startY: number, endX: number, endY: number, w: number, h: number) => {
    const x1 = Math.min(startX, endX);
    const y1 = Math.min(startY, endY);
    const x2 = Math.max(startX, endX);
    const y2 = Math.max(startY, endY);
    return { x: x1 / w, y: y1 / h, width: (x2 - x1) / w, height: (y2 - y1) / h };
  };

  const finishRect = useCallback(
    (startX: number, startY: number, endX: number, endY: number) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const nr = normRect(startX - rect.left, startY - rect.top, endX - rect.left, endY - rect.top, rect.width, rect.height);
      if (nr.width < 0.02 || nr.height < 0.02) return;

      const corners2d: [number, number][] = [
        [startX, startY],
        [endX, startY],
        [endX, endY],
        [startX, endY],
      ];
      const corners3d = hasMesh
        ? corners2d
            .map(([cx, cy]) => raycastRef.current(cx, cy))
            .filter((p): p is THREE.Vector3 => p !== null)
            .map((p) => [p.x, p.y, p.z] as [number, number, number])
        : undefined;

      onRectMarkComplete?.({ ...nr, color: "#0F3D91", corners3d: corners3d?.length === 4 ? corners3d : undefined });
    },
    [hasMesh, onRectMarkComplete]
  );

  const onPointerDown = (e: React.PointerEvent) => {
    if (!markMode) return;
    e.preventDefault();
    setDrawing({ startX: e.clientX, startY: e.clientY, curX: e.clientX, curY: e.clientY });
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drawing || !markMode) return;
    setDrawing((d) => (d ? { ...d, curX: e.clientX, curY: e.clientY } : null));
  };

  const onPointerUp = (e: React.PointerEvent) => {
    if (!drawing || !markMode) return;
    finishRect(drawing.startX, drawing.startY, e.clientX, e.clientY);
    setDrawing(null);
  };

  return (
    <div
      ref={containerRef}
      className={`cad-viewport-grid relative h-full w-full min-h-0 ${className}`}
      style={{ cursor: markMode ? "crosshair" : selectMode ? "pointer" : "default" }}
    >
      {markMode && (
        <div
          className="absolute inset-0 z-10 cursor-crosshair"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />
      )}

      {!hasMesh && sourcePreview && (
        <div
          className="absolute inset-0 flex items-center justify-center p-6"
          style={{ backgroundColor: EDITOR_SURFACE }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={sourcePreview} alt="Source" className="max-h-full max-w-full object-contain shadow-sm" />
        </div>
      )}

      {modelLoadStatus === "loading" && hasMesh && (
        <div
          className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center"
          style={{ backgroundColor: `${EDITOR_SURFACE}e6` }}
        >
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border-subtle bg-panel-bg px-8 py-5 shadow-md">
            <Loader2 className="h-7 w-7 animate-spin text-primary-container" />
            <p className="text-body-sm font-medium text-on-surface">Loading 3D model…</p>
          </div>
        </div>
      )}

      {modelLoadStatus === "error" && (
        <div
          className="absolute inset-0 z-30 flex items-center justify-center p-8 text-center"
          style={{ backgroundColor: EDITOR_SURFACE }}
        >
          <div className="max-w-md rounded-xl border border-error/30 bg-panel-bg px-6 py-5 shadow-md">
            <p className="text-body-sm font-medium text-error">
              Could not display the 3D model.
            </p>
            <p className="mt-2 text-body-sm text-on-surface-variant">
              {modelLoadDetail ?? "Try Generate Model again from the Source panel."}
            </p>
          </div>
        </div>
      )}

      {(hasMesh || !sourcePreview) && (
        <Canvas
          shadows
          gl={{ antialias: true }}
          className="!absolute inset-0"
          camera={{ fov: CAMERA.PHI_FOV, position: [3, 2.5, 4], near: 0.01, far: 500 }}
          onCreated={({ gl }) => {
            gl.outputColorSpace = THREE.SRGBColorSpace;
            gl.toneMapping = THREE.ACESFilmicToneMapping;
            gl.toneMappingExposure = 1.05;
          }}
        >
          <SceneContent
            meshData={meshData}
            modelUrl={modelUrl}
            modelFormat={modelFormat}
            mtlUrl={mtlUrl}
            wireframe={wireframe}
            rectMarks={rectMarks}
            meshGroupRef={meshGroupRef}
            controlsRef={controlsRef}
            markMode={markMode}
            selectMode={selectMode}
            onMeshSelect={onMeshSelect}
            onHomeReady={handleHomeReady}
            segmentParts={segmentParts}
            activePartId={activePartId}
            modelSelected={modelSelected}
            fitGeneration={fitGeneration}
            onModelLoaded={handleModelLoaded}
            onModelError={handleModelError}
          />
          <RaycastBridge meshGroupRef={meshGroupRef} raycastRef={raycastRef} />
        </Canvas>
      )}

      {rectMarks?.map((m) => (
        <div
          key={m.id}
          className="pointer-events-none absolute border-2 border-primary-container bg-primary-container/10"
          style={{
            left: `${m.x * 100}%`,
            top: `${m.y * 100}%`,
            width: `${m.width * 100}%`,
            height: `${m.height * 100}%`,
          }}
        >
          {m.text && (
            <span className="absolute -top-5 left-0 rounded bg-primary-container px-1.5 py-0.5 text-[10px] text-on-primary">
              {m.text}
            </span>
          )}
        </div>
      ))}

      {drawing && containerRef.current && (
        <div
          className="pointer-events-none absolute border-2 border-dashed border-ai-purple bg-ai-purple/10"
          style={{
            left: Math.min(drawing.startX, drawing.curX) - containerRef.current.getBoundingClientRect().left,
            top: Math.min(drawing.startY, drawing.curY) - containerRef.current.getBoundingClientRect().top,
            width: Math.abs(drawing.curX - drawing.startX),
            height: Math.abs(drawing.curY - drawing.startY),
          }}
        />
      )}
    </div>
  );
});
