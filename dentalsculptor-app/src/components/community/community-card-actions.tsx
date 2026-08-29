"use client";

import { useState } from "react";
import { Check, Copy, Download, Heart, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CommunityCardActions({ projectId, initialLikes }: { projectId: string; initialLikes: number }) {
  const [liked, setLiked] = useState(false);
  const [likes, setLikes] = useState(initialLikes);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function toggleLike() {
    setBusy(true);
    try {
      const response = await fetch(`/api/community/${projectId}/like`, { method: "POST" });
      const data = (await response.json()) as { liked?: boolean; likes?: number; error?: string };
      if (!response.ok) throw new Error(data.error ?? "Could not update like.");
      setLiked(Boolean(data.liked));
      setLikes(data.likes ?? likes);
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const url = new URL(`/community/${projectId}`, window.location.origin).toString();
    if (navigator.share) await navigator.share({ title: "DentalSculptor teaching project", url });
    else {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    }
  }

  return (
    <div className="mt-4 grid grid-cols-4 gap-1.5" aria-label="Community project actions">
      <Button size="sm" variant="outline" disabled={busy} onClick={() => void toggleLike()} className={cn("px-2", liked && "border-red-300 bg-red-50 text-red-700")} aria-label={`${liked ? "Unlike" : "Like"} project`}>
        <Heart className={cn("mr-1 h-3.5 w-3.5", liked && "fill-current")} />{likes}
      </Button>
      <Button size="sm" variant="outline" asChild className="px-2">
        <a href={`/api/community/${projectId}/model?download=1`} download><Download className="mr-1 h-3.5 w-3.5" />Download</a>
      </Button>
      <form action={`/api/community/${projectId}/clone`} method="POST">
        <Button size="sm" variant="outline" type="submit" className="w-full px-2"><Copy className="mr-1 h-3.5 w-3.5" />Clone</Button>
      </form>
      <Button size="sm" variant="outline" onClick={() => void share()} className="px-2" aria-label="Share project">
        {copied ? <Check className="mr-1 h-3.5 w-3.5" /> : <Share2 className="mr-1 h-3.5 w-3.5" />}{copied ? "Copied" : "Share"}
      </Button>
    </div>
  );
}
