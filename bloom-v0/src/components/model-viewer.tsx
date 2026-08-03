'use client';

import React, { Suspense, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, Center, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import ErrorBoundary from './ErrorBoundary';

// Helper component to load and display the GLB model using useGLTF
function Model({ url }: { url: string }) {
  // useGLTF simplifies loading GLB/GLTF files and accessing their scene graph
  const { scene } = useGLTF(url);
  // Optional: Clone the scene to avoid modifying the original cache
  const clonedScene = scene.clone(); 

  // Optional: Traverse the scene to enable shadows if needed
  useEffect(() => {
    clonedScene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
  }, [clonedScene]);

  // primitive object allows rendering loaded scenes directly
  return <primitive object={clonedScene} />;
}

interface ModelViewerProps {
  modelUrl: string;
  style?: React.CSSProperties; // Allow passing custom styles
}

export function ModelViewer({ modelUrl, style }: ModelViewerProps) {
  // Fallback UI for the ErrorBoundary
  const fallback = (
    <div style={{ padding: '20px', textAlign: 'center', color: 'orange', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <h3>Error Loading 3D Model</h3>
        <p>Could not load model from:</p>
        <p style={{ wordBreak: 'break-all' }}>{modelUrl}</p>
        <p style={{ marginTop: '10px', fontSize: '0.8em' }}>(Please check the file path and ensure the file exists or is served correctly)</p>
    </div>
  );

  return (
    <ErrorBoundary fallback={fallback}>
      <div style={{ height: '500px', width: '100%', background: '#f0f0f0', ...style }}>
        <Canvas shadows camera={{ position: [0, 2, 5], fov: 50 }}>
          <ambientLight intensity={1.0} /> {/* Increased ambient light slightly */} 
          <directionalLight 
            position={[10, 10, 5]} 
            intensity={2.0} // Increased directional light slightly
            castShadow 
            shadow-mapSize-width={1024} // Optional: Improve shadow quality
            shadow-mapSize-height={1024}
          />
          <Suspense fallback={null}>
            <Center>
              {/* Use the updated Model component for GLB */}
              <Model url={modelUrl} />
            </Center>
          </Suspense>
          <Grid 
            infiniteGrid 
            cellSize={0.5} 
            sectionSize={5} 
            sectionColor={"#ababab"}
            fadeDistance={50}
            fadeStrength={1}
          />
          <OrbitControls makeDefault />
          {/* Optional: Add Environment for better lighting/reflections, often good for GLB */}
          {/* <Environment preset="sunset" /> */}
        </Canvas>
      </div>
    </ErrorBoundary>
  );
} 