"use client";

import {
  Suspense,
  useRef,
  useMemo,
  useState,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from "react";
import { Canvas, ThreeEvent, useThree } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, Html, Grid, Environment } from "@react-three/drei";
import * as THREE from "three";
import type { GeneratedMesh } from "@/lib/model-generator";
import { RemoteModelMesh } from "@/components/three/remote-model-mesh";
import type { RemoteModelFormat } from "@/lib/model-format";
import { VIEWPORT_THEME } from "@/lib/constants";

export interface AnnotationMarker {
  id: string;
  text: string;
  position: [number, number, number];
  color?: string;
}

interface DentalModelProps {
  meshData?: GeneratedMesh | null;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  mtlUrl?: string | null;
  wireframe?: boolean;
  transparency?: number;
  onSurfaceClick?: (point: THREE.Vector3) => void;
  annotations?: AnnotationMarker[];
  selectedAnnotationId?: string | null;
}

function DentalMesh({
  meshData,
  wireframe,
  transparency = 1,
  onSurfaceClick,
}: Omit<DentalModelProps, "annotations" | "selectedAnnotationId" | "modelUrl">) {
  const geometry = useMemo(() => {
    if (meshData?.vertices?.length) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(meshData.vertices, 3));
      if (meshData.normals?.length) {
        geo.setAttribute("normal", new THREE.Float32BufferAttribute(meshData.normals, 3));
      } else {
        geo.computeVertexNormals();
      }
      if (meshData.indices?.length) {
        geo.setIndex(meshData.indices);
      }
      if (meshData.uvs?.length) {
        geo.setAttribute("uv", new THREE.Float32BufferAttribute(meshData.uvs, 2));
      }
      return geo;
    }

    return new THREE.CylinderGeometry(0.5, 0.35, 1.8, 32, 8, false);
  }, [meshData]);

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      onSurfaceClick?.(e.point);
    },
    [onSurfaceClick]
  );

  return (
    <mesh geometry={geometry} onClick={handleClick} castShadow receiveShadow>
      <meshStandardMaterial
        color="#f5e6d3"
        roughness={0.45}
        metalness={0.05}
        wireframe={wireframe}
        transparent={transparency < 1}
        opacity={transparency}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function GltfModelWrapper(props: {
  url: string;
  format?: RemoteModelFormat | string | null;
  mtlUrl?: string | null;
  wireframe?: boolean;
  transparency?: number;
  onSurfaceClick?: (point: THREE.Vector3) => void;
}) {
  return (
    <RemoteModelMesh
      url={props.url}
      format={props.format}
      mtlUrl={props.mtlUrl}
      wireframe={props.wireframe}
      transparency={props.transparency}
      onSurfaceClick={props.onSurfaceClick}
    />
  );
}

function AnnotationPoints({
  annotations,
  selectedId,
}: {
  annotations: AnnotationMarker[];
  selectedId?: string | null;
}) {
  return (
    <>
      {annotations.map((ann) => (
        <group key={ann.id} position={ann.position}>
          <mesh>
            <sphereGeometry args={[0.04, 16, 16]} />
            <meshStandardMaterial
              color={ann.color ?? "#0F3D91"}
              emissive={selectedId === ann.id ? ann.color ?? "#0F3D91" : "#000000"}
              emissiveIntensity={selectedId === ann.id ? 0.5 : 0}
            />
          </mesh>
          <Html distanceFactor={8} position={[0, 0.08, 0]} center>
            <div className="glass-panel max-w-[180px] rounded-lg px-2 py-1 text-xs shadow-sm">
              {ann.text}
            </div>
          </Html>
        </group>
      ))}
    </>
  );
}

function ViewerCaptureBridge({
  captureRef,
}: {
  captureRef: React.MutableRefObject<(() => Promise<Blob | null>) | null>;
}) {
  const { camera, gl, scene } = useThree();
  captureRef.current = () =>
    new Promise((resolve) => {
      camera.updateMatrixWorld();
      camera.updateProjectionMatrix();
      gl.render(scene, camera);

      const rect = gl.domElement.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      const output = document.createElement("canvas");
      output.width = width;
      output.height = height;
      const context = output.getContext("2d");
      if (!context) {
        resolve(null);
        return;
      }
      context.drawImage(gl.domElement, 0, 0, width, height);
      output.toBlob((blob) => resolve(blob), "image/png", 0.92);
    });
  return null;
}

function SceneContent(
  props: DentalModelProps & {
    captureRef: React.MutableRefObject<(() => Promise<Blob | null>) | null>;
  }
) {
  const controlsRef = useRef<any>(null);

  return (
    <>
      <ViewerCaptureBridge captureRef={props.captureRef} />
      <PerspectiveCamera makeDefault position={[2.5, 1.5, 2.5]} fov={45} />
      <color attach="background" args={[VIEWPORT_THEME.background]} />
      <Environment preset="studio" environmentIntensity={0.55} />
      <ambientLight intensity={0.65} />
      <hemisphereLight args={["#ffffff", "#d1d5db", 0.55]} />
      <directionalLight position={[5, 8, 5]} intensity={1.1} castShadow />
      <directionalLight position={[-3, 4, -2]} intensity={0.45} />
      <Grid
        args={[10, 10]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor={VIEWPORT_THEME.grid}
        sectionSize={2}
        sectionThickness={1}
        sectionColor={VIEWPORT_THEME.gridSection}
        fadeDistance={12}
        position={[0, -1.2, 0]}
      />
      {props.modelUrl ? (
        <GltfModelWrapper
          url={props.modelUrl}
          format={props.modelFormat}
          mtlUrl={props.mtlUrl}
          wireframe={props.wireframe}
          transparency={props.transparency}
          onSurfaceClick={props.onSurfaceClick}
        />
      ) : (
        <DentalMesh
          meshData={props.meshData}
          wireframe={props.wireframe}
          transparency={props.transparency}
          onSurfaceClick={props.onSurfaceClick}
        />
      )}
      {props.annotations && (
        <AnnotationPoints
          annotations={props.annotations}
          selectedId={props.selectedAnnotationId}
        />
      )}
      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.08}
        minDistance={1}
        maxDistance={8}
        target={[0, 0.2, 0]}
      />
    </>
  );
}

export interface DentalViewerHandle {
  capturePreview: () => Promise<Blob | null>;
}

export interface DentalViewerProps extends DentalModelProps {
  className?: string;
  showGrid?: boolean;
}

export const DentalViewer = forwardRef<DentalViewerHandle, DentalViewerProps>(function DentalViewer(
  { className = "h-full w-full", ...props },
  ref
) {
  const captureRef = useRef<(() => Promise<Blob | null>) | null>(null);
  useImperativeHandle(ref, () => ({
    capturePreview: () => captureRef.current?.() ?? Promise.resolve(null),
  }));

  return (
    <div className={`relative ${className}`} style={{ backgroundColor: VIEWPORT_THEME.background }}>
      <Canvas
        shadows
        gl={{ antialias: true, alpha: true }}
        onCreated={({ gl }) => {
          gl.outputColorSpace = THREE.SRGBColorSpace;
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.05;
        }}
      >
        <Suspense fallback={null}>
          <SceneContent {...props} captureRef={captureRef} />
        </Suspense>
      </Canvas>
    </div>
  );
});

export function useViewerControls() {
  const [wireframe, setWireframe] = useState(false);
  const [transparency, setTransparency] = useState(1);
  const [sectionView, setSectionView] = useState(false);

  return {
    wireframe,
    setWireframe,
    transparency,
    setTransparency,
    sectionView,
    setSectionView,
  };
}

export function ViewerToolbar({
  wireframe,
  onWireframeToggle,
  transparency,
  onTransparencyChange,
  onReset,
  onFullscreen,
}: {
  wireframe: boolean;
  onWireframeToggle: () => void;
  transparency: number;
  onTransparencyChange: (v: number) => void;
  onReset: () => void;
  onFullscreen: () => void;
}) {
  return (
    <div className="absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1 rounded-xl border border-border-subtle bg-panel-bg/90 p-1 backdrop-blur-md workbench-shadow">
      <ToolbarButton active={wireframe} onClick={onWireframeToggle} label="Wireframe" />
      <ToolbarButton
        active={transparency < 1}
        onClick={() => onTransparencyChange(transparency < 1 ? 1 : 0.5)}
        label="Transparency"
      />
      <ToolbarButton onClick={onReset} label="Reset" />
      <ToolbarButton onClick={onFullscreen} label="Fullscreen" />
    </div>
  );
}

function ToolbarButton({
  onClick,
  label,
  active,
}: {
  onClick: () => void;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-3 py-1.5 text-label-caps transition-colors ${
        active
          ? "bg-primary-container text-on-primary"
          : "text-on-surface-variant hover:bg-surface-container-low"
      }`}
    >
      {label}
    </button>
  );
}
