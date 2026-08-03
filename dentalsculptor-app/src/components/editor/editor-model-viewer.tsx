"use client";

import { Suspense, useMemo, useCallback } from "react";
import { Canvas, ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Center, Grid, Html } from "@react-three/drei";
import * as THREE from "three";
import type { GeneratedMesh } from "@/lib/model-generator";
import type { AnnotationMarker } from "@/components/three/dental-viewer";

interface EditorModelProps {
  meshData?: GeneratedMesh | null;
  wireframe?: boolean;
  transparency?: number;
  onSurfaceClick?: (point: THREE.Vector3) => void;
  annotations?: AnnotationMarker[];
}

function EditorMesh({
  meshData,
  wireframe,
  transparency = 1,
  onSurfaceClick,
}: Omit<EditorModelProps, "annotations">) {
  const geometry = useMemo(() => {
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
        roughness={0.4}
        metalness={0.05}
        wireframe={wireframe}
        transparent={transparency < 1}
        opacity={transparency}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

function AnnotationMarkers({ annotations }: { annotations: AnnotationMarker[] }) {
  return (
    <>
      {annotations.map((ann) => (
        <group key={ann.id} position={ann.position}>
          <mesh>
            <sphereGeometry args={[0.04, 16, 16]} />
            <meshStandardMaterial color={ann.color ?? "#0F3D91"} emissive={ann.color ?? "#0F3D91"} emissiveIntensity={0.3} />
          </mesh>
          <Html distanceFactor={8} position={[0, 0.08, 0]} center>
            <div className="glass-panel max-w-[180px] rounded-lg px-2 py-1 text-xs shadow-sm">{ann.text}</div>
          </Html>
        </group>
      ))}
    </>
  );
}

function EditorScene({ meshData, wireframe, transparency, onSurfaceClick, annotations }: EditorModelProps) {
  return (
    <>
      <ambientLight intensity={1.0} />
      <directionalLight position={[10, 10, 5]} intensity={2.0} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
      <Suspense fallback={null}>
        <Center>
          <EditorMesh meshData={meshData} wireframe={wireframe} transparency={transparency} onSurfaceClick={onSurfaceClick} />
        </Center>
        {annotations && annotations.length > 0 && <AnnotationMarkers annotations={annotations} />}
      </Suspense>
      <Grid
        infiniteGrid
        cellSize={0.5}
        sectionSize={5}
        cellColor="#E2E8F0"
        sectionColor="#CBD5E1"
        fadeDistance={50}
        fadeStrength={1}
        position={[0, -1.2, 0]}
      />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} minDistance={1} maxDistance={10} target={[0, 0.2, 0]} />
    </>
  );
}

export function getMeshStats(meshData?: GeneratedMesh | null) {
  if (!meshData?.vertices?.length) {
    return { vertices: 0, polygons: 0 };
  }
  const vertices = meshData.vertices.length / 3;
  const polygons = meshData.indices?.length ? meshData.indices.length / 3 : vertices / 3;
  return {
    vertices: Math.round(vertices),
    polygons: Math.round(polygons),
  };
}

export function EditorModelViewer({
  meshData,
  wireframe,
  transparency,
  onSurfaceClick,
  annotations,
  className = "h-full w-full",
}: EditorModelProps & { className?: string }) {
  return (
    <div className={`relative ${className}`}>
      <Canvas shadows camera={{ position: [0, 2, 5], fov: 50 }} gl={{ antialias: true }}>
        <EditorScene
          meshData={meshData}
          wireframe={wireframe}
          transparency={transparency}
          onSurfaceClick={onSurfaceClick}
          annotations={annotations}
        />
      </Canvas>
    </div>
  );
}

export function AxisIndicator() {
  return (
    <div className="absolute bottom-6 left-6 flex items-center gap-2">
      <div className="relative h-12 w-12">
        <div className="absolute bottom-0 left-6 h-10 w-px origin-bottom bg-red-500" />
        <div className="absolute bottom-0 left-6 h-px w-10 origin-left bg-green-500" />
        <div className="absolute bottom-0 left-6 h-10 w-px origin-bottom rotate-[-45deg] bg-blue-500" />
        <span className="absolute -top-1 left-5 text-[10px] font-bold text-red-600">Y</span>
        <span className="absolute bottom-0 right-0 text-[10px] font-bold text-green-600">X</span>
        <span className="absolute left-0 top-1 text-[10px] font-bold text-blue-600">Z</span>
      </div>
    </div>
  );
}

export function ViewportStats({ vertices, polygons }: { vertices: number; polygons: number }) {
  return (
    <div className="glass-panel absolute bottom-32 right-6 z-10 flex flex-col gap-1 rounded-lg border border-border-subtle px-4 py-2 shadow-sm">
      <div className="flex items-center justify-between gap-8">
        <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Vertices</span>
        <span className="text-label-mono text-xs text-on-surface">{vertices.toLocaleString()}</span>
      </div>
      <div className="flex items-center justify-between gap-8">
        <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Polygons</span>
        <span className="text-label-mono text-xs text-on-surface">{polygons.toLocaleString()}</span>
      </div>
      <div className="flex items-center justify-between gap-8">
        <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Camera</span>
        <span className="text-label-mono text-xs text-on-surface">Perspective</span>
      </div>
    </div>
  );
}
