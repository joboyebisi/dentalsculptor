"use client";

import { useParams } from "next/navigation";
import { WebXRViewer } from "@/components/three/webxr-viewer";
import { useResearchTracker } from "@/hooks/use-research-tracker";
import { useEffect, useState } from "react";

export default function XRPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { track } = useResearchTracker();
  const [title, setTitle] = useState("XR Experience");

  useEffect(() => {
    fetch(`/api/projects/${projectId}`)
      .then((r) => r.json())
      .then((d) => setTitle(d.project?.title ?? "XR Experience"));
  }, [projectId]);

  return (
    <WebXRViewer
      projectTitle={title}
      className="h-screen"
      onLaunch={() => track("XR_LAUNCHED", projectId)}
    />
  );
}
