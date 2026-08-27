"use client";

import { useState } from "react";
import { Check, Heart, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CommunityActions({ projectId, initialLikes, initialLiked }: { projectId: string; initialLikes: number; initialLiked: boolean }) {
  const [liked, setLiked] = useState(initialLiked);
  const [likes, setLikes] = useState(initialLikes);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  async function toggleLike() {
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

  return <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={() => void toggleLike()} className={cn(liked && "border-red-300 bg-red-50 text-red-700")}><Heart className={cn("mr-2 h-4 w-4", liked && "fill-current")} />{liked ? "Liked" : "Like"} · {likes}</Button><Button className="bg-primary-container text-on-primary" onClick={() => void share()}>{copied ? <Check className="mr-2 h-4 w-4" /> : <Share2 className="mr-2 h-4 w-4" />}{copied ? "Link copied" : "Share"}</Button></div>;
}
