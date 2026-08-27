"use client";

import { useParams } from "next/navigation";
import { PostGenerationAction } from "@/components/projects/post-generation-action";

export default function ProjectDownloadPage() {
  const { id } = useParams<{ id: string }>();
  return <PostGenerationAction projectId={id} action="download" />;
}
