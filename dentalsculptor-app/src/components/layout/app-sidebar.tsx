"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderOpen,
  Users,
  GraduationCap,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavItems } from "@/hooks/use-nav-items";
import { UserMenu } from "@/components/auth/user-menu";
import { AppLogo, AppLogoMark } from "@/components/brand/app-logo";

const isPreview = process.env.NEXT_PUBLIC_UI_PREVIEW_MODE === "true";

const iconMap = {
  LayoutDashboard,
  FolderOpen,
  Users,
  GraduationCap,
  BarChart3,
  Settings,
};

export function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const navItems = useNavItems();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border-subtle bg-panel-bg transition-all duration-200",
        collapsed ? "w-16" : "w-sidebar-width"
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border-subtle px-3">
        {collapsed ? (
          <AppLogoMark size="xs" className="mx-auto" />
        ) : (
          <AppLogo size="sm" href="/dashboard" className="min-w-0" wordmarkClassName="truncate text-base" />
        )}
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
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
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border-subtle p-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="mb-3 flex w-full items-center justify-center rounded-lg p-2 text-on-surface-variant hover:bg-surface-container-low"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
        <div className="flex items-center gap-3 px-2">
          {isPreview ? (
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container">
              <User className="h-4 w-4 text-on-surface-variant" />
            </div>
          ) : (
            <UserMenu />
          )}
          {!collapsed && (
            <span className="text-body-sm text-on-surface-variant">Account</span>
          )}
        </div>
      </div>
    </aside>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />
      <main className="ml-sidebar-width min-h-screen">{children}</main>
    </div>
  );
}
