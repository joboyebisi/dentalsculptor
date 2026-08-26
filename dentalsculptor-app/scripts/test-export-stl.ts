/**
 * Smoke test: STL export produces valid binary with clinical-scale bbox.
 * Run: npx tsx scripts/test-export-stl.ts
 */

import * as THREE from "three";
import {
  geometryToBinaryStl,
  validateBinaryStlBuffer,
  validateGeometry,
} from "../src/lib/export-mesh";
import { getExportPreset } from "../src/lib/export-presets";

function makeIcosphereGeometry(radiusMeters: number): THREE.BufferGeometry {
  const geo = new THREE.IcosahedronGeometry(radiusMeters, 4);
  return geo.toNonIndexed();
}

function normalizeLikeExport(geo: THREE.BufferGeometry): THREE.BufferGeometry {
  const clone = geo.clone();
  clone.computeBoundingBox();
  const size = new THREE.Vector3();
  clone.boundingBox!.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z);
  const scale = maxDim <= 0.05 ? 1000 : maxDim < 4 ? 12 / maxDim : 1;
  clone.scale(scale, scale, scale);
  clone.computeVertexNormals();
  return clone;
}

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error("FAIL:", message);
    process.exit(1);
  }
  console.log("OK:", message);
}

const raw = makeIcosphereGeometry(0.006);
const normalized = normalizeLikeExport(raw);
const preset = getExportPreset("simodont");
const validation = validateGeometry(normalized, preset);

assert(validation.triangleCount > 100, `triangle count ${validation.triangleCount}`);
assert(
  validation.boundingBoxMm.x >= 4 && validation.boundingBoxMm.y >= 4,
  `clinical bbox mm: ${JSON.stringify(validation.boundingBoxMm)}`
);

const stl = geometryToBinaryStl(normalized);
const check = validateBinaryStlBuffer(stl);
assert(check.ok, `STL valid with ${check.triangleCount} triangles`);
assert(stl.byteLength === 84 + check.triangleCount * 50, "STL byte size matches spec");

console.log("\nAll export STL tests passed.");
