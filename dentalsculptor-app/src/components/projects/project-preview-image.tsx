"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { resolveModelFetchUrl } from "@/lib/model-asset-url";

export function ProjectPreviewImage({
  src,
  alt,
  className,
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const resolved = src && !failed ? resolveModelFetchUrl(src) : null;
  const isLocal = resolved?.startsWith("/") ?? false;

  if (!resolved) {
    return (
      <div
        className={cn(
          "shrink-0 bg-gradient-to-br from-surface-container to-primary-container/10",
          className ?? "aspect-video"
        )}
        aria-hidden
      />
    );
  }

  return (
    <div className={cn("relative shrink-0 overflow-hidden bg-surface-container", className ?? "aspect-video")}>
      <Image
        src={resolved}
        alt={alt}
        fill
        unoptimized={!isLocal}
        className="object-cover object-center"
        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        onError={() => setFailed(true)}
      />
    </div>
  );
}
