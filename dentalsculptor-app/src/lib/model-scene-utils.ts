import * as THREE from "three";

/** Centre and scale a loaded mesh so it fits the editor viewport (~2 units). */
export function normalizeModelRoot(root: THREE.Object3D, targetSize = 1.8): void {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return;

  const center = box.getCenter(new THREE.Vector3());
  root.position.sub(center);

  root.updateMatrixWorld(true);
  const sized = new THREE.Box3().setFromObject(root);
  const dims = sized.getSize(new THREE.Vector3());
  const maxDim = Math.max(dims.x, dims.y, dims.z, 0.001);
  const scale = targetSize / maxDim;
  root.scale.setScalar(scale);

  root.updateMatrixWorld(true);
  const grounded = new THREE.Box3().setFromObject(root);
  root.position.y -= grounded.min.y;
}

export function countMeshes(root: THREE.Object3D): number {
  let count = 0;
  root.traverse((child) => {
    if (child instanceof THREE.Mesh) count += 1;
  });
  return count;
}
