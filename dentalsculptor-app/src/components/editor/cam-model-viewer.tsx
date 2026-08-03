"use client";

import { useRef, useMemo, useCallback, useEffect, useState, forwardRef, useImperativeHandle } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import type { GeneratedMesh } from "@/lib/model-generator";
import {
  CAMERA,
  computeDefaultCameraPosition,
  computeDefaultPerspectiveCameraFrustum,
  type Coordinate,
} from "@/lib/camera-utils";

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

interface CamModelViewerProps {
  meshData?: GeneratedMesh | null;
  sourcePreview?: string | null;
  wireframe?: boolean;
  rectMarks?: RectMark[];
  markMode?: boolean;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  onRectMarkComplete?: (mark: Omit<RectMark, "id" | "text">) => void;
  className?: string;
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

function MeshGroup({
  meshData,
  wireframe,
  meshGroupRef,
  selectMode,
  onMeshSelect,
}: {
  meshData?: GeneratedMesh | null;
  wireframe?: boolean;
  meshGroupRef: React.RefObject<THREE.Group | null>;
  selectMode?: boolean;
  onMeshSelect?: () => void;
}) {
  const geometry = useMemo(() => buildGeometry(meshData), [meshData]);

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
          color="#e8dcc8"
          specular="#ffffff"
          shininess={24}
          wireframe={wireframe}
          side={THREE.DoubleSide}
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
}: {
  meshGroupRef: React.RefObject<THREE.Group | null>;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  onReady: (home: { position: Coordinate; target: Coordinate }) => void;
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
    const t = setTimeout(fitCamera, 50);
    return () => clearTimeout(t);
  }, [fitCamera]);

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
  wireframe,
  rectMarks,
  meshGroupRef,
  controlsRef,
  markMode,
  selectMode,
  onMeshSelect,
  onHomeReady,
}: {
  meshData?: GeneratedMesh | null;
  wireframe?: boolean;
  rectMarks?: RectMark[];
  meshGroupRef: React.RefObject<THREE.Group | null>;
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
  markMode?: boolean;
  selectMode?: boolean;
  onMeshSelect?: () => void;
  onHomeReady: (home: { position: Coordinate; target: Coordinate }) => void;
}) {
  return (
    <>
      <color attach="background" args={["#e8ecf0"]} />
      <ambientLight intensity={0.9} />
      <directionalLight position={[8, 10, 6]} intensity={1.4} castShadow />
      <directionalLight position={[-5, 3, -4]} intensity={0.35} />

      <MeshGroup
        meshData={meshData}
        wireframe={wireframe}
        meshGroupRef={meshGroupRef}
        selectMode={selectMode}
        onMeshSelect={onMeshSelect}
      />

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

      <CameraRig meshGroupRef={meshGroupRef} controlsRef={controlsRef} onReady={onHomeReady} />
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
    sourcePreview,
    wireframe,
    rectMarks,
    markMode,
    selectMode,
    onMeshSelect,
    onRectMarkComplete,
    className = "h-full w-full",
  },
  ref
) {
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const raycastRef = useRef<(x: number, y: number) => THREE.Vector3 | null>(() => null);
  const homeRef = useRef<{ position: Coordinate; target: Coordinate } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [drawing, setDrawing] = useState<{ startX: number; startY: number; curX: number; curY: number } | null>(null);

  const hasMesh = Boolean(meshData?.vertices?.length);

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
      className={`cad-viewport-grid relative ${className}`}
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
        <div className="absolute inset-0 flex items-center justify-center p-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={sourcePreview} alt="Source" className="max-h-full max-w-full object-contain shadow-sm" />
        </div>
      )}

      {(hasMesh || !sourcePreview) && (
        <Canvas
          shadows
          gl={{ antialias: true }}
          className="!absolute inset-0"
          camera={{ fov: CAMERA.PHI_FOV, position: [3, 2.5, 4], near: 0.01, far: 500 }}
        >
          <SceneContent
            meshData={meshData}
            wireframe={wireframe}
            rectMarks={rectMarks}
            meshGroupRef={meshGroupRef}
            controlsRef={controlsRef}
            markMode={markMode}
            selectMode={selectMode}
            onMeshSelect={onMeshSelect}
            onHomeReady={handleHomeReady}
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
