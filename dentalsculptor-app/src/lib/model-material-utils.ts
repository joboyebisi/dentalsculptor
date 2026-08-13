import * as THREE from "three";
import { VIEWPORT_THEME } from "@/lib/constants";

const TEXTURE_KEYS = [
  "map",
  "normalMap",
  "roughnessMap",
  "metalnessMap",
  "aoMap",
  "emissiveMap",
  "bumpMap",
] as const;

function materialLuminance(mat: THREE.Material): number {
  if ("color" in mat && mat.color instanceof THREE.Color) {
    return mat.color.r + mat.color.g + mat.color.b;
  }
  return 1;
}

function textureReady(tex?: THREE.Texture | null): boolean {
  if (!tex?.image) return false;
  const img = tex.image as { width?: number; height?: number; data?: unknown };
  if (typeof img.width === "number" && img.width > 0) return true;
  return Boolean(img.data);
}

function fixTextureColorSpace(tex?: THREE.Texture | null): void {
  if (tex && "colorSpace" in tex) {
    tex.colorSpace = THREE.SRGBColorSpace;
  }
}

/** Make fal/OBJ/GLB materials readable under editor lighting (fixes flat black PBR). */
export function fixModelMaterials(root: THREE.Object3D): void {
  root.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;

    const mats = Array.isArray(child.material) ? child.material : [child.material];
    mats.forEach((mat) => {
      if (!mat) return;

      TEXTURE_KEYS.forEach((key) => {
        if (key in mat) {
          fixTextureColorSpace((mat as Record<string, THREE.Texture | undefined>)[key]);
        }
      });

      if (mat instanceof THREE.MeshStandardMaterial) {
        if (!textureReady(mat.map)) {
          mat.map = null;
        }
        if (!mat.envMap && mat.metalness > 0.35) {
          mat.metalness = 0.08;
          mat.roughness = Math.max(mat.roughness, 0.55);
        }
        if (materialLuminance(mat) < 0.08 && !textureReady(mat.map)) {
          mat.color.set(VIEWPORT_THEME.meshDefault);
        }
        mat.envMapIntensity = mat.envMap ? 1 : 0;
      }

      if (
        mat instanceof THREE.MeshPhongMaterial ||
        mat instanceof THREE.MeshLambertMaterial
      ) {
        if (mat.map && !textureReady(mat.map)) {
          mat.map = null;
        }
        if (materialLuminance(mat) < 0.08) {
          mat.color.set(VIEWPORT_THEME.meshDefault);
        }
      }
    });
  });
}

export function getAssetBaseUrl(url: string): string {
  const clean = url.split("?")[0] ?? url;
  const idx = clean.lastIndexOf("/");
  return idx >= 0 ? clean.slice(0, idx + 1) : "";
}
