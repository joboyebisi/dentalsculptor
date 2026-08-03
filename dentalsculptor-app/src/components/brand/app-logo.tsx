import Image from "next/image";
import Link from "next/link";
import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

const sizeMap = {
  xs: { box: 24, className: "h-6 w-6" },
  sm: { box: 28, className: "h-7 w-7" },
  md: { box: 32, className: "h-8 w-8" },
  lg: { box: 48, className: "h-12 w-12" },
  xl: { box: 64, className: "h-16 w-16" },
} as const;

type AppLogoSize = keyof typeof sizeMap;

interface AppLogoProps {
  showWordmark?: boolean;
  size?: AppLogoSize;
  href?: string | null;
  className?: string;
  wordmarkClassName?: string;
}

export function AppLogo({
  showWordmark = true,
  size = "md",
  href = "/",
  className,
  wordmarkClassName,
}: AppLogoProps) {
  const { box, className: imgClass } = sizeMap[size];

  const content = (
    <>
      <Image
        src="/logo.png"
        alt={`${APP_NAME} logo`}
        width={box}
        height={box}
        className={cn("shrink-0 object-contain", imgClass)}
        priority={size === "lg" || size === "xl"}
      />
      {showWordmark && (
        <span
          className={cn(
            "text-headline-md font-bold text-primary-container",
            wordmarkClassName
          )}
        >
          {APP_NAME}
        </span>
      )}
    </>
  );

  const wrapperClass = cn("flex items-center gap-2.5", className);

  if (href) {
    return (
      <Link href={href} className={cn(wrapperClass, "hover:opacity-90")}>
        {content}
      </Link>
    );
  }

  return <div className={wrapperClass}>{content}</div>;
}

export function AppLogoMark({ size = "sm", className }: { size?: AppLogoSize; className?: string }) {
  return <AppLogo showWordmark={false} size={size} href={null} className={className} />;
}
