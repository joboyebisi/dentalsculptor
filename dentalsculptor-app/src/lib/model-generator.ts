/**
 * Procedural dental model generation from uploaded images.
 * Creates an editable tooth-like mesh for the 3D editor.
 * In production, this would connect to an AI reconstruction pipeline.
 */

export interface GeneratedMesh {
  vertices: number[];
  indices: number[];
  normals: number[];
  uvs: number[];
}

export function generateDentalMeshFromImage(
  imageWidth: number,
  imageHeight: number
): GeneratedMesh {
  const segments = 32;
  const rings = 24;
  const vertices: number[] = [];
  const indices: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];

  const aspect = imageWidth / Math.max(imageHeight, 1);
  const crownHeight = 1.2;
  const rootDepth = 0.8;
  const maxRadius = 0.55 * Math.min(aspect, 1.2);

  for (let ring = 0; ring <= rings; ring++) {
    const t = ring / rings;
    const y = crownHeight - t * (crownHeight + rootDepth);
    let radius: number;

    if (t < 0.35) {
      radius = maxRadius * (0.85 + 0.15 * Math.sin(t * Math.PI * 4));
    } else if (t < 0.55) {
      radius = maxRadius * (1 - (t - 0.35) * 0.4);
    } else {
      radius = maxRadius * (0.92 - (t - 0.55) * 1.8);
      radius = Math.max(radius, 0.05);
    }

    for (let seg = 0; seg <= segments; seg++) {
      const theta = (seg / segments) * Math.PI * 2;
      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;
      const bulge = t < 0.4 ? Math.sin(theta * 2) * 0.04 : 0;

      vertices.push(x + bulge, y, z);

      const nx = x / Math.max(radius, 0.001);
      const nz = z / Math.max(radius, 0.001);
      normals.push(nx, 0.3, nz);

      uvs.push(seg / segments, t);
    }
  }

  for (let ring = 0; ring < rings; ring++) {
    for (let seg = 0; seg < segments; seg++) {
      const a = ring * (segments + 1) + seg;
      const b = a + segments + 1;
      indices.push(a, b, a + 1);
      indices.push(b, b + 1, a + 1);
    }
  }

  return { vertices, indices, normals, uvs };
}

export function meshToGLBPlaceholder(mesh: GeneratedMesh): string {
  return JSON.stringify(mesh);
}
