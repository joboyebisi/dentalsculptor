"use client";

import { useMemo, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { Grid, OrbitControls, TransformControls } from "@react-three/drei";
import * as THREE from "three";
import { RemoteModelMesh } from "@/components/three/remote-model-mesh";
import { jawSocketPose, type JawPlacement } from "@/lib/jaw-placement";
import type { RemoteModelFormat } from "@/lib/model-format";

export type PlacementTool = "translate" | "rotate" | "scale";
const VIEW_SCALE = 0.05;
const TOOTH_BASE_SCALE = 0.72;

function pose(placement: JawPlacement) {
  const socket = jawSocketPose(placement.arch, placement.fdiTooth);
  return {
    position: new THREE.Vector3(
      (socket.positionMm[0] + placement.positionMm[0]) * VIEW_SCALE,
      (socket.positionMm[1] + placement.positionMm[1]) * VIEW_SCALE,
      (socket.positionMm[2] + placement.positionMm[2]) * VIEW_SCALE
    ),
    rotation: new THREE.Euler(
      THREE.MathUtils.degToRad(placement.rotationDeg[0] + (placement.arch === "upper" ? 180 : 0)),
      THREE.MathUtils.degToRad(placement.rotationDeg[1] + socket.yawDeg),
      THREE.MathUtils.degToRad(placement.rotationDeg[2]),
      "XYZ"
    ),
    scale: placement.scale * TOOTH_BASE_SCALE,
    socket,
  };
}

function TrainingJaw({ arch }: { arch: "upper" | "lower" }) {
  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i += 1) {
      const angle = Math.PI * (0.1 + (i / 64) * 0.8);
      points.push(new THREE.Vector3(Math.cos(angle) * 1.9, 0, Math.sin(angle) * 1.5 - 0.8));
    }
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 128, 0.31, 14, false);
  }, []);
  return <group position={[0, arch === "lower" ? 0 : -0.7, 0]} rotation={arch === "upper" ? [Math.PI, 0, 0] : undefined}>
    <mesh geometry={geometry} receiveShadow castShadow>
      <meshStandardMaterial color="#c8b5a8" roughness={0.8} transparent opacity={0.88} />
    </mesh>
  </group>;
}

function InteractiveScene({ placement, tool, modelUrl, modelFormat, onChange }: {
  placement: JawPlacement;
  tool: PlacementTool;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  onChange: (placement: JawPlacement) => void;
}) {
  const toothRef = useRef<THREE.Group>(null);
  const current = pose(placement);

  const commitTransform = () => {
    const object = toothRef.current;
    if (!object) return;
    const baseX = placement.arch === "upper" ? 180 : 0;
    const uniformScale = Math.max(0.7, Math.min(1.3, object.scale.x / TOOTH_BASE_SCALE));
    onChange({
      ...placement,
      positionMm: [
        object.position.x / VIEW_SCALE - current.socket.positionMm[0],
        object.position.y / VIEW_SCALE - current.socket.positionMm[1],
        object.position.z / VIEW_SCALE - current.socket.positionMm[2],
      ].map((value) => Math.round(value * 10) / 10) as [number, number, number],
      rotationDeg: [
        THREE.MathUtils.radToDeg(object.rotation.x) - baseX,
        THREE.MathUtils.radToDeg(object.rotation.y) - current.socket.yawDeg,
        THREE.MathUtils.radToDeg(object.rotation.z),
      ].map((value) => Math.round(value)) as [number, number, number],
      scale: Math.round(uniformScale * 100) / 100,
    });
  };

  return <>
    <color attach="background" args={["#e7edf4"]} />
    <ambientLight intensity={0.8} />
    <directionalLight position={[5, 8, 6]} intensity={1.4} castShadow />
    <Grid args={[10, 10]} cellSize={0.25} sectionSize={1} fadeDistance={12} position={[0, -0.02, 0]} />
    <TrainingJaw arch={placement.arch} />
    <TransformControls
      mode={tool}
      space={tool === "translate" ? "world" : "local"}
      translationSnap={0.05}
      rotationSnap={THREE.MathUtils.degToRad(2)}
      scaleSnap={0.01}
      size={0.8}
      onMouseUp={commitTransform}
    >
      <group ref={toothRef} position={current.position} rotation={current.rotation} scale={current.scale}>
        {modelUrl ? <RemoteModelMesh url={modelUrl} format={modelFormat} /> : <mesh castShadow><cylinderGeometry args={[0.45, 0.32, 1.6, 24]} /><meshStandardMaterial color="#f1ead7" /></mesh>}
      </group>
    </TransformControls>
    <OrbitControls makeDefault target={[0, 0.3, 0]} minDistance={2.5} maxDistance={10} />
  </>;
}

export function JawPlacementCanvas(props: {
  placement: JawPlacement;
  tool: PlacementTool;
  modelUrl?: string | null;
  modelFormat?: RemoteModelFormat | string | null;
  onChange: (placement: JawPlacement) => void;
}) {
  return <div className="h-[390px] overflow-hidden rounded-xl border border-outline-variant bg-[#e7edf4]">
    <Canvas shadows camera={{ position: [4.2, 3.2, 5], fov: 42, near: 0.01, far: 100 }}>
      <InteractiveScene {...props} />
    </Canvas>
  </div>;
}
