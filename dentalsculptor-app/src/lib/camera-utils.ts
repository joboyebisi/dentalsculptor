/** CAD-style camera utilities (McCleery / Anneal viewer pattern). */

export type Coordinate = { x: number; y: number; z: number };

export interface SerializedCameraState {
  projection: "perspective" | "orthographic";
  projectionMatrix: number[];
  viewMatrix: number[];
  worldMatrix: number[];
  position: [number, number, number];
  quaternion: [number, number, number, number];
  target: [number, number, number];
  width: number;
  height: number;
}

export const CAMERA = {
  HOME_AZIMUTH: 45,
  HOME_ELEVATION: 35.264,
  PHI_FOV: 45,
  ZOOM_SCALAR: 1.5,
  X_FAR_SCALAR: 5,
  X_NEAR_SCALAR: 0.05,
  X_NEAR_DEFAULT: 0.1,
  CONTROL_DAMPING: 0.08,
} as const;

export function deg2rad(angle: number): number {
  return (angle * Math.PI) / 180;
}

export function computeVisibleHeightFromAngleAndRadius(phiFov: number, radius: number): number {
  const thetaRad = deg2rad(phiFov / 2);
  const visibleHalfHeight = radius / Math.cos(thetaRad);
  return 2 * visibleHalfHeight;
}

export function calculateDistanceFromAngleAndHeight(phiFov: number, visibleHeight: number): number {
  const thetaRad = deg2rad(phiFov / 2);
  const h = visibleHeight / 2;
  return h / Math.tan(thetaRad);
}

export function convertToCartesian(azimuth: number, elevation: number, distance: number): Coordinate {
  const azimuthRad = deg2rad(azimuth);
  const elevationRad = deg2rad(elevation);
  return {
    x: distance * Math.cos(elevationRad) * Math.sin(azimuthRad),
    y: distance * Math.sin(elevationRad),
    z: distance * Math.cos(elevationRad) * Math.cos(azimuthRad),
  };
}

export function computeDefaultCameraPosition(
  phiFov: number,
  objectRadius: number,
  objectCenter: Coordinate,
  azimuth: number,
  elevation: number,
  zoomScalar: number
): { position: Coordinate; distance: number } {
  const height = computeVisibleHeightFromAngleAndRadius(phiFov, objectRadius);
  const distance = calculateDistanceFromAngleAndHeight(phiFov, height) * zoomScalar;
  const coords = convertToCartesian(azimuth, elevation, distance);
  return {
    position: {
      x: coords.x + objectCenter.x,
      y: coords.y + objectCenter.y,
      z: coords.z + objectCenter.z,
    },
    distance,
  };
}

export function computeDefaultPerspectiveCameraFrustum(
  objectRadius: number,
  cameraDistanceFromTarget: number
): { near: number; far: number } {
  const l = cameraDistanceFromTarget;
  const r = objectRadius;
  return {
    far: (l + r) * CAMERA.X_FAR_SCALAR,
    near: Math.min((l - r) * CAMERA.X_NEAR_SCALAR, CAMERA.X_NEAR_DEFAULT),
  };
}
