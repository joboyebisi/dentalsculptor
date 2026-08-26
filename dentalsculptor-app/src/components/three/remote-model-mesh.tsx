"use client";



import { useEffect, useMemo, useState, useCallback, useRef } from "react";

import { ThreeEvent } from "@react-three/fiber";

import * as THREE from "three";

import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";

import { MTLLoader } from "three/examples/jsm/loaders/MTLLoader.js";

import { detectModelFormat, type RemoteModelFormat } from "@/lib/model-format";

import { resolveModelFetchUrl } from "@/lib/model-asset-url";
import { glbValidationError, isValidGlbBuffer } from "@/lib/glb-utils";

import { VIEWPORT_THEME } from "@/lib/constants";

import { countMeshes, normalizeModelRoot } from "@/lib/model-scene-utils";
import { fixModelMaterials, getAssetBaseUrl } from "@/lib/model-material-utils";



export interface RemoteModelMeshProps {

  url: string;

  format?: RemoteModelFormat | string | null;

  mtlUrl?: string | null;

  wireframe?: boolean;

  transparency?: number;

  onSurfaceClick?: (point: THREE.Vector3) => void;

  onClick?: (e: ThreeEvent<MouseEvent>) => void;

  onClone?: (root: THREE.Object3D) => void;

  onLoaded?: (info: { meshCount: number }) => void;

  onError?: (message: string) => void;

}



function applySurfaceMaterials(

  root: THREE.Object3D,

  wireframe?: boolean,

  transparency?: number

) {

  root.traverse((child) => {

    if (!(child instanceof THREE.Mesh)) return;

    child.castShadow = true;

    child.receiveShadow = true;

    const mats = Array.isArray(child.material) ? child.material : [child.material];

    let hasValidMat = false;

    mats.forEach((mat) => {

      if (!mat) return;

      hasValidMat = true;

      if (

        mat instanceof THREE.MeshStandardMaterial ||

        mat instanceof THREE.MeshPhongMaterial ||

        mat instanceof THREE.MeshLambertMaterial

      ) {

        mat.wireframe = Boolean(wireframe);

        if (transparency !== undefined && transparency < 1) {

          mat.transparent = true;

          mat.opacity = transparency;

        }

        mat.side = THREE.DoubleSide;

      }

    });

    if (!hasValidMat) {

      child.material = new THREE.MeshStandardMaterial({

        color: VIEWPORT_THEME.meshDefault,

        roughness: 0.55,

        metalness: 0.05,

        side: THREE.DoubleSide,

        wireframe: Boolean(wireframe),

      });

    }

  });

}



function prepareClone(

  root: THREE.Object3D,

  wireframe?: boolean,

  transparency?: number

): THREE.Object3D {

  normalizeModelRoot(root);
  applySurfaceMaterials(root, wireframe, transparency);
  fixModelMaterials(root);
  return root;

}



function isGlbBytes(bytes: ArrayBuffer): boolean {

  if (bytes.byteLength < 4) return false;

  return new DataView(bytes).getUint32(0, true) === 0x46546c67;

}



function isObjBytes(bytes: ArrayBuffer): boolean {

  const head = new TextDecoder().decode(bytes.slice(0, Math.min(bytes.byteLength, 256))).trimStart();

  return (

    head.startsWith("v ") ||

    head.startsWith("#") ||

    head.startsWith("mtllib") ||

    head.startsWith("o ") ||

    head.startsWith("g ")

  );

}



function resolveLoadFormat(

  bytes: ArrayBuffer,

  hint?: RemoteModelFormat | string | null

): RemoteModelFormat {

  if (isGlbBytes(bytes)) return "glb";

  if (isObjBytes(bytes)) return "obj";

  if (hint === "glb" || hint === "obj") return hint;

  return "glb";

}



async function fetchModelBytes(url: string): Promise<ArrayBuffer> {

  const fetchUrl = resolveModelFetchUrl(url);

  const res = await fetch(fetchUrl, { credentials: "same-origin" });

  if (!res.ok) {

    throw new Error(`Could not fetch model (${res.status})`);

  }

  return res.arrayBuffer();

}



async function fetchTextAsset(url: string): Promise<string> {

  const fetchUrl = resolveModelFetchUrl(url);

  const res = await fetch(fetchUrl, { credentials: "same-origin" });

  if (!res.ok) {

    throw new Error(`Could not fetch material file (${res.status})`);

  }

  return res.text();

}



function parseGlb(bytes: ArrayBuffer): Promise<THREE.Object3D> {
  const loader = new GLTFLoader();
  if (!isValidGlbBuffer(bytes)) {
    return Promise.reject(new Error(glbValidationError(bytes)));
  }
  return loader.parseAsync(bytes, "").then((gltf) => gltf.scene);
}



function parseObj(text: string, materials?: MTLLoader.MaterialCreator): THREE.Group {

  const loader = new OBJLoader();

  if (materials) {

    materials.preload();

    loader.setMaterials(materials);

  }

  return loader.parse(text);

}



async function loadMaterials(mtlUrl: string): Promise<MTLLoader.MaterialCreator | undefined> {
  try {
    const mtlText = await fetchTextAsset(mtlUrl);
    const mtlBase = getAssetBaseUrl(mtlUrl);

    return await new Promise((resolve) => {
      const manager = new THREE.LoadingManager(
        () => resolve(materials),
        undefined,
        () => resolve(materials)
      );
      manager.setURLModifier((path) => {
        try {
          const absolute = /^https?:\/\//i.test(path) ? path : new URL(path, mtlBase).href;
          return resolveModelFetchUrl(absolute);
        } catch {
          return resolveModelFetchUrl(path);
        }
      });

      const mtlLoader = new MTLLoader(manager);
      mtlLoader.setResourcePath(mtlBase);
      const materials = mtlLoader.parse(mtlText, mtlBase);
      materials.preload();
    });
  } catch (error) {
    console.warn("[RemoteModelMesh] MTL load failed, continuing without materials:", error);
    return undefined;
  }
}



async function loadModelRoot(

  url: string,

  formatHint?: RemoteModelFormat | string | null,

  mtlUrl?: string | null

): Promise<THREE.Object3D> {

  const bytes = await fetchModelBytes(url);

  const format = resolveLoadFormat(bytes, formatHint);

  const materials = mtlUrl ? await loadMaterials(mtlUrl) : undefined;



  if (format === "obj") {

    const text = new TextDecoder().decode(bytes);

    return parseObj(text, materials);

  }



  try {

    return await parseGlb(bytes);

  } catch (glbError) {

    if (isObjBytes(bytes)) {

      const text = new TextDecoder().decode(bytes);

      return parseObj(text, materials);

    }

    throw glbError;

  }

}



function RemoteModelInner({

  url,

  format,

  mtlUrl,

  wireframe,

  transparency,

  onSurfaceClick,

  onClick,

  onClone,

  onLoaded,

  onError,

}: RemoteModelMeshProps) {

  const [root, setRoot] = useState<THREE.Object3D | null>(null);

  const onCloneRef = useRef(onClone);

  const onLoadedRef = useRef(onLoaded);

  const onErrorRef = useRef(onError);

  onCloneRef.current = onClone;

  onLoadedRef.current = onLoaded;

  onErrorRef.current = onError;



  useEffect(() => {

    let cancelled = false;

    setRoot(null);



    loadModelRoot(url, format, mtlUrl)

      .then((loaded) => {

        if (!cancelled) setRoot(loaded);

      })

      .catch((error) => {

        console.error("[RemoteModelMesh] load failed:", error);

        const message = error instanceof Error ? error.message : "Could not load 3D model.";

        if (!cancelled) onErrorRef.current?.(message);

      });



    return () => {

      cancelled = true;

    };

  }, [url, format, mtlUrl]);



  const cloned = useMemo(() => {

    if (!root) return null;

    return prepareClone(root.clone(true), wireframe, transparency);

  }, [root, wireframe, transparency]);



  useEffect(() => {

    if (!cloned) return;

    onCloneRef.current?.(cloned);

    onLoadedRef.current?.({ meshCount: countMeshes(cloned) });

  }, [cloned]);



  const handleClick = useCallback(

    (e: ThreeEvent<MouseEvent>) => {

      e.stopPropagation();

      onClick?.(e);

      onSurfaceClick?.(e.point);

    },

    [onClick, onSurfaceClick]

  );



  if (!cloned) return null;

  return <primitive object={cloned} onClick={handleClick} />;

}



/** Load a remote GLB/GLTF or OBJ (+ optional MTL) via same-origin proxy when needed. */

export function RemoteModelMesh(props: RemoteModelMeshProps) {

  const format = detectModelFormat(props.url, props.format, props.mtlUrl);

  return <RemoteModelInner {...props} format={format} />;

}


