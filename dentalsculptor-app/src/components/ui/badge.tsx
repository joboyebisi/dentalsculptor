import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "ai" | "research" | "success" | "warning" | "outline";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-label-caps uppercase tracking-wider",
        {
          "bg-primary-container/10 text-primary-container": variant === "default",
          "bg-ai-purple/10 text-ai-purple": variant === "ai",
          "bg-research-indigo/10 text-research-indigo": variant === "research",
          "bg-secondary/10 text-secondary": variant === "success",
          "bg-warning/10 text-warning": variant === "warning",
          "border border-border-subtle text-on-surface-variant": variant === "outline",
        },
        className
      )}
      {...props}
    />
  );
}
