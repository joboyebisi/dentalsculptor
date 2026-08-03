"use client";

import { Suspense, useRef, useMemo, useState, useCallback } from "react";
import { Canvas, useThree, ThreeEvent } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, Html, Grid } from "@react-three/drei";
import * as THREE from "three";
import type { GeneratedMesh } from "@/lib/model-generator";

export interface AnnotationMarker {
  id: string;
  text: string;
  position: [number, number, number];
  color?: string;
}

interface DentalModelProps {
  meshData?: GeneratedMesh | null;
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
}: Omit<DentalModelProps, "annotations" | "selectedAnnotationId">) {
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

function SceneContent(props: DentalModelProps) {
  const controlsRef = useRef<any>(null);

  return (
    <>
      <PerspectiveCamera makeDefault position={[2.5, 1.5, 2.5]} fov={45} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
      <directionalLight position={[-3, 4, -2]} intensity={0.4} />
      <Grid
        args={[10, 10]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor="#E2E8F0"
        sectionSize={2}
        sectionThickness={1}
        sectionColor="#CBD5E1"
        fadeDistance={12}
        position={[0, -1.2, 0]}
      />
      <DentalMesh
        meshData={props.meshData}
        wireframe={props.wireframe}
        transparency={props.transparency}
        onSurfaceClick={props.onSurfaceClick}
      />
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

export interface DentalViewerProps extends DentalModelProps {
  className?: string;
  showGrid?: boolean;
}

export function DentalViewer({
  className = "h-full w-full",
  ...props
}: DentalViewerProps) {
  return (
    <div className={`relative bg-surface-container-low ${className}`}>
      <Canvas shadows gl={{ antialias: true, alpha: true }}>
        <Suspense fallback={null}>
          <SceneContent {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}

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
