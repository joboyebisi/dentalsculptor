/**
 * Server-side mesh export — load GLB/OBJ, validate, emit STL/GLB for simulator presets.
 */

import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import type { ExportPreset } from "@/lib/export-presets";

export interface ExportValidationReport {
  triangleCount: number;
  maxTriangles: number;
  withinTriangleBudget: boolean;
  watertight: boolean;
  watertightNote: string;
  units: string;
  boundingBoxMm: { x: number; y: number; z: number };
  scaleApplied: number;
  warnings: string[];
  errors: string[];
  passed: boolean;
}

export interface ExportMeshResult {
  buffer: Buffer;
  contentType: string;
  filename: string;
  extension: string;
  validation: ExportValidationReport;
}

function quantizeEdge(a: THREE.Vector3, b: THREE.Vector3, precision = 4): string {
  const k = 10 ** precision;
  const ax = Math.round(a.x * k);
  const ay = Math.round(a.y * k);
  const az = Math.round(a.z * k);
  const bx = Math.round(b.x * k);
  const by = Math.round(b.y * k);
  const bz = Math.round(b.z * k);
  if (ax < bx || (ax === bx && ay < by) || (ax === bx && ay === by && az < bz)) {
    return `${ax},${ay},${az}|${bx},${by},${bz}`;
  }
  return `${bx},${by},${bz}|${ax},${ay},${az}`;
}

/** Heuristic manifold/watertight check — each undirected edge appears exactly twice. */
export function checkWatertight(geometry: THREE.BufferGeometry): {
  watertight: boolean;
  note: string;
} {
  const geo = geometry.index ? geometry : geometry.toNonIndexed();
  const pos = geo.getAttribute("position");
  if (!pos || pos.count < 3) {
    return { watertight: false, note: "Mesh has no triangles." };
  }

  const edgeCounts = new Map<string, number>();
  for (let i = 0; i < pos.count; i += 3) {
    const v0 = new THREE.Vector3().fromBufferAttribute(pos, i);
    const v1 = new THREE.Vector3().fromBufferAttribute(pos, i + 1);
    const v2 = new THREE.Vector3().fromBufferAttribute(pos, i + 2);
    for (const e of [
      quantizeEdge(v0, v1),
      quantizeEdge(v1, v2),
      quantizeEdge(v2, v0),
    ]) {
      edgeCounts.set(e, (edgeCounts.get(e) ?? 0) + 1);
    }
  }

  let openEdges = 0;
  for (const count of edgeCounts.values()) {
    if (count !== 2) openEdges += 1;
  }

  if (openEdges === 0) {
    return { watertight: true, note: "All edges paired — mesh appears closed." };
  }
  return {
    watertight: false,
    note: `${openEdges} edge(s) not shared by exactly two triangles — holes or non-manifold geometry likely.`,
  };
}

function mergeSceneMeshes(object: THREE.Object3D): THREE.BufferGeometry {
  const geometries: THREE.BufferGeometry[] = [];
  object.updateMatrixWorld(true);
  object.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      const mesh = child as THREE.Mesh;
      const geom = mesh.geometry.clone();
      geom.applyMatrix4(mesh.matrixWorld);
      geometries.push(geom);
    }
  });

  if (geometries.length === 0) {
    throw new Error("No mesh geometry found in model.");
  }

  if (geometries.length === 1) return geometries[0];

  const merged = new THREE.BufferGeometry();
  const positions: number[] = [];
  for (const g of geometries) {
    const pos = g.getAttribute("position");
    for (let i = 0; i < pos.count; i++) {
      positions.push(pos.getX(i), pos.getY(i), pos.getZ(i));
    }
  }
  merged.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  return merged.toNonIndexed();
}

function normalizeToMm(geometry: THREE.BufferGeometry, preset: ExportPreset): THREE.BufferGeometry {
  const geo = geometry.clone();
  geo.computeBoundingBox();
  const box = geo.boundingBox!;
  const size = new THREE.Vector3();
  box.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;

  // Tooth-sized normalization: target ~12 mm longest axis if model is unitless or huge/tiny.
  const targetMm = 12;
  let scale = preset.scaleFactor;
  if (maxDim > 0 && maxDim < 50) {
    // Likely already mm-ish
    scale = preset.scaleFactor;
  } else if (maxDim <= 2) {
    // Meters (glTF default) → mm
    scale = 1000 * preset.scaleFactor;
  } else {
    scale = (targetMm / maxDim) * preset.scaleFactor;
  }

  geo.scale(scale, scale, scale);
  if (preset.upAxis === "Y") {
    // Clinical Y-up — no rotation for most dental exports
  }
  geo.computeVertexNormals();
  return geo;
}

function decimateIfNeeded(geometry: THREE.BufferGeometry, maxTriangles: number): THREE.BufferGeometry {
  const triCount = geometry.index
    ? geometry.index.count / 3
    : geometry.getAttribute("position").count / 3;
  if (triCount <= maxTriangles) return geometry;

  // Uniform stride decimation (simple; replace with quadric on Modal CPU later).
  const step = Math.ceil(triCount / maxTriangles);
  const src = geometry.index ? geometry : geometry.toNonIndexed();
  const pos = src.getAttribute("position");
  const out: number[] = [];
  for (let i = 0; i < pos.count; i += 3 * step) {
    for (let j = 0; j < 3 && i + j < pos.count; j++) {
      out.push(pos.getX(i + j), pos.getY(i + j), pos.getZ(i + j));
    }
  }
  const dec = new THREE.BufferGeometry();
  dec.setAttribute("position", new THREE.Float32BufferAttribute(out, 3));
  dec.computeVertexNormals();
  return dec;
}

export function geometryToBinaryStl(geometry: THREE.BufferGeometry): Buffer {
  const geo = geometry.index ? geometry.toNonIndexed() : geometry;
  const pos = geo.getAttribute("position");
  const triCount = pos.count / 3;

  const buffer = Buffer.alloc(84 + 4 + triCount * 50);
  buffer.writeUInt32LE(triCount, 80);

  let offset = 84;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const cb = new THREE.Vector3();
  const ab = new THREE.Vector3();
  const normal = new THREE.Vector3();

  for (let i = 0; i < pos.count; i += 3) {
    a.fromBufferAttribute(pos, i);
    b.fromBufferAttribute(pos, i + 1);
    c.fromBufferAttribute(pos, i + 2);
    cb.subVectors(c, b);
    ab.subVectors(a, b);
    normal.crossVectors(cb, ab).normalize();

    buffer.writeFloatLE(normal.x, offset);
    buffer.writeFloatLE(normal.y, offset + 4);
    buffer.writeFloatLE(normal.z, offset + 8);
    buffer.writeFloatLE(a.x, offset + 12);
    buffer.writeFloatLE(a.y, offset + 16);
    buffer.writeFloatLE(a.z, offset + 20);
    buffer.writeFloatLE(b.x, offset + 24);
    buffer.writeFloatLE(b.y, offset + 28);
    buffer.writeFloatLE(b.z, offset + 32);
    buffer.writeFloatLE(c.x, offset + 36);
    buffer.writeFloatLE(c.y, offset + 40);
    buffer.writeFloatLE(c.z, offset + 44);
    buffer.writeUInt16LE(0, offset + 48);
    offset += 50;
  }

  return buffer;
}

export function validateGeometry(
  geometry: THREE.BufferGeometry,
  preset: ExportPreset
): ExportValidationReport {
  const geo = geometry.index ? geometry : geometry.toNonIndexed();
  const triCount = geo.getAttribute("position").count / 3;
  geo.computeBoundingBox();
  const size = new THREE.Vector3();
  geo.boundingBox!.getSize(size);

  const { watertight, note } = checkWatertight(geo);
  const warnings: string[] = [];
  const errors: string[] = [];

  if (!watertight && preset.requireWatertight) {
    warnings.push(note);
  }
  if (triCount > preset.maxTriangles) {
    warnings.push(
      `Triangle count ${triCount.toLocaleString()} exceeds budget — will decimate to ~${preset.maxTriangles.toLocaleString()}.`
    );
  }

  const passed =
    errors.length === 0 &&
    (!preset.requireWatertight || watertight) &&
    triCount > 0;

  return {
    triangleCount: Math.floor(triCount),
    maxTriangles: preset.maxTriangles,
    withinTriangleBudget: triCount <= preset.maxTriangles,
    watertight,
    watertightNote: note,
    units: preset.units,
    boundingBoxMm: {
      x: Math.round(size.x * 100) / 100,
      y: Math.round(size.y * 100) / 100,
      z: Math.round(size.z * 100) / 100,
    },
    scaleApplied: preset.scaleFactor,
    warnings,
    errors,
    passed,
  };
}

async function loadMeshFromBuffer(
  buffer: ArrayBuffer,
  format: "glb" | "obj"
): Promise<THREE.BufferGeometry> {
  if (format === "glb") {
    const loader = new GLTFLoader();
    const gltf = await loader.parseAsync(buffer, "");
    return mergeSceneMeshes(gltf.scene);
  }
  const text = new TextDecoder().decode(buffer);
  const loader = new OBJLoader();
  return mergeSceneMeshes(loader.parse(text));
}

export async function loadMeshFromUrl(
  modelUrl: string,
  format: "glb" | "obj"
): Promise<THREE.BufferGeometry> {
  const res = await fetch(modelUrl, {
    headers: { "User-Agent": "DentalSculptor-Export/1.0" },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model (${res.status}).`);
  }
  const buffer = await res.arrayBuffer();
  return loadMeshFromBuffer(buffer, format);
}

export async function exportMeshForPreset(
  modelUrl: string,
  format: "glb" | "obj",
  preset: ExportPreset,
  options?: { validateOnly?: boolean }
): Promise<ExportMeshResult | { validation: ExportValidationReport }> {
  let geometry = await loadMeshFromUrl(modelUrl, format);
  geometry = normalizeToMm(geometry, preset);
  const preValidation = validateGeometry(geometry, preset);
  geometry = decimateIfNeeded(geometry, preset.maxTriangles);
  const validation = validateGeometry(geometry, preset);

  if (options?.validateOnly) {
    return { validation: { ...validation, warnings: [...preValidation.warnings, ...validation.warnings] } };
  }

  const primaryFormat = preset.formats[0];

  if (primaryFormat === "glb" && format === "glb") {
    const res = await fetch(modelUrl, { headers: { "User-Agent": "DentalSculptor-Export/1.0" } });
    if (!res.ok) throw new Error(`Failed to fetch GLB (${res.status}).`);
    const buffer = Buffer.from(await res.arrayBuffer());
    return {
      buffer,
      contentType: "model/gltf-binary",
      filename: "export.glb",
      extension: "glb",
      validation,
    };
  }

  const stl = geometryToBinaryStl(geometry);
  return {
    buffer: stl,
    contentType: "model/stl",
    filename: "export.stl",
    extension: "stl",
    validation,
  };
}
