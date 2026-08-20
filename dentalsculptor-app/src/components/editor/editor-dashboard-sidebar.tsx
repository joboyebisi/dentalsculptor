"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderOpen,
  Users,
  GraduationCap,
  BarChart3,
  Settings,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { UserMenu } from "@/components/auth/user-menu";
import { AppLogo } from "@/components/brand/app-logo";

const isPreview = process.env.NEXT_PUBLIC_UI_PREVIEW_MODE === "true";

const iconMap = {
  LayoutDashboard,
  FolderOpen,
  Users,
  GraduationCap,
  BarChart3,
  Settings,
};

interface EditorDashboardSidebarProps {
  open: boolean;
}

export function EditorDashboardSidebar({ open }: EditorDashboardSidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "editor-scrollbar flex h-full shrink-0 flex-col overflow-hidden border-r border-outline-variant bg-panel-bg transition-all duration-200",
        open ? "w-sidebar-width" : "w-0 border-r-0"
      )}
    >
      <div className="flex h-14 min-w-sidebar-width items-center border-b border-border-subtle px-3">
        <AppLogo size="sm" href="/dashboard" className="min-w-0" wordmarkClassName="truncate text-base" />
      </div>

      <nav className="min-w-sidebar-width flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = iconMap[item.icon as keyof typeof iconMap];
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex items-center gap-3 rounded-lg px-3 py-2 text-body-sm transition-colors hover:bg-surface-container-low",
                isActive && "active-nav bg-surface-container-low",
                !isActive && "text-on-surface-variant"
              )}
            >
              <Icon className="h-5 w-5 shrink-0" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="min-w-sidebar-width border-t border-border-subtle p-3">
        <div className="flex items-center gap-3 px-2">
          {isPreview ? (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container">
              <User className="h-4 w-4 text-on-surface-variant" />
            </div>
          ) : (
            <UserMenu />
          )}
          <span className="text-body-sm text-on-surface-variant">Account</span>
        </div>
      </div>
    </aside>
  );
}
