"use client";

import { useParams } from "next/navigation";
import { PostGenerationAction } from "@/components/projects/post-generation-action";

export default function ProjectPublishPage() {
  const { id } = useParams<{ id: string }>();
  return <PostGenerationAction projectId={id} action="publish" />;
}
