"use client";

import { useState } from "react";
import { Check, Copy, Download, Heart, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { WebMcpTool, webMcpResult } from "@/components/webmcp/webmcp-tool";

export function CommunityActions({ projectId, projectTitle, initialLikes, initialLiked, signedIn = true }: { projectId: string; projectTitle: string; initialLikes: number; initialLiked: boolean; signedIn?: boolean }) {
  const [liked, setLiked] = useState(initialLiked);
  const [likes, setLikes] = useState(initialLikes);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  async function toggleLike() {
    if (!signedIn) {
      window.location.href = `/sign-in?redirect_url=${encodeURIComponent(`/community/${projectId}`)}`;
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`/api/community/${projectId}/like`, { method: "POST" });
      const data = (await response.json()) as { liked?: boolean; likes?: number; error?: string };
      if (!response.ok) throw new Error(data.error ?? "Could not update like.");
      setLiked(Boolean(data.liked));
      setLikes(data.likes ?? likes);
    } finally { setBusy(false); }
  }

  async function share() {
    const url = window.location.href;
    if (navigator.share) await navigator.share({ title: "DentalSculptor project", url });
    else { await navigator.clipboard.writeText(url); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }
  }

  return <>
    <WebMcpTool name="dentalsculptor_inspect_published_model"
      description="Inspect the published dental teaching model and its community interaction state."
      readOnly execute={() => webMcpResult(`Published model: ${projectTitle}.`, {
        projectId, title: projectTitle, likes, likedByCurrentUser: liked, signedIn,
        downloadUrl: `/api/community/${projectId}/model?download=1`, shareUrl: window.location.href,
      })} />
    <WebMcpTool name="dentalsculptor_get_published_share_link"
      description="Get the canonical browser URL for this published dental model without changing community state."
      readOnly execute={() => webMcpResult(window.location.href, { url: window.location.href })} />
    <WebMcpTool name="dentalsculptor_toggle_published_like"
      description="Like or unlike this published dental model. DentalSculptor will request sign-in when required."
      enabled={!busy} execute={async () => {
        await toggleLike();
        return webMcpResult(signedIn ? "Updated the like state." : "Opened sign-in to continue liking.");
      }} />
    <WebMcpTool name="dentalsculptor_download_published_model"
      description="Download the published dental model through DentalSculptor's validated model endpoint."
      execute={() => {
        const url = `/api/community/${projectId}/model?download=1`;
        window.location.assign(url);
        return webMcpResult("Started the published model download.", { url });
      }} />
    <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={() => void toggleLike()} className={cn(liked && "border-red-300 bg-red-50 text-red-700")}><Heart className={cn("mr-2 h-4 w-4", liked && "fill-current")} />{liked ? "Liked" : signedIn ? "Like" : "Sign in to like"} · {likes}</Button><Button variant="outline" asChild><a href={`/api/community/${projectId}/model?download=1`} download><Download className="mr-2 h-4 w-4" />Download</a></Button>{signedIn ? <form action={`/api/community/${projectId}/clone`} method="POST"><Button variant="outline" type="submit"><Copy className="mr-2 h-4 w-4" />Clone</Button></form> : <Button variant="outline" asChild><a href={`/sign-in?redirect_url=${encodeURIComponent(`/community/${projectId}`)}`}><Copy className="mr-2 h-4 w-4" />Sign in to clone</a></Button>}<Button className="bg-primary-container text-on-primary" onClick={() => void share()}>{copied ? <Check className="mr-2 h-4 w-4" /> : <Share2 className="mr-2 h-4 w-4" />}{copied ? "Link copied" : "Share"}</Button></div>
  </>;
}
