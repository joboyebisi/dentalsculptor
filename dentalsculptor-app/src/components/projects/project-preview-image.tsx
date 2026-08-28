"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { isCardPreviewServeUrl } from "@/lib/project-card-preview-path";

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
  const resolved = src && !failed ? src : null;
  const isApiPreview = resolved ? isCardPreviewServeUrl(resolved) : false;
  const isLocalStatic = resolved?.startsWith("/") && !isApiPreview;

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

  if (isApiPreview) {
    return (
      <div className={cn("relative shrink-0 overflow-hidden bg-surface-container", className ?? "aspect-video")}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={resolved}
          alt={alt}
          className="h-full w-full object-cover object-center"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }

  return (
    <div className={cn("relative shrink-0 overflow-hidden bg-surface-container", className ?? "aspect-video")}>
      <Image
        src={resolved}
        alt={alt}
        fill
        unoptimized={!isLocalStatic}
        className="object-cover object-center"
        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
        onError={() => setFailed(true)}
      />
    </div>
  );
}
