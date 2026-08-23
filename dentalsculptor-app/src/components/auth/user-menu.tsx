"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogOut, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

export function UserMenu({ collapsed = false }: { collapsed?: boolean }) {
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className={cn("flex w-full flex-col gap-2", collapsed && "items-center")}>
      {!collapsed && (
        <Button variant="ghost" size="sm" asChild className="h-8 w-full justify-start px-2 text-body-sm">
          <Link href="/settings">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Link>
        </Button>
      )}
      <Button
        variant="outline"
        size="sm"
        className={cn(
          "gap-2 text-body-sm",
          collapsed ? "h-8 w-8 px-0" : "h-8 w-full justify-start px-3"
        )}
        onClick={handleSignOut}
        aria-label="Sign out"
      >
        <LogOut className="h-4 w-4 shrink-0" />
        {!collapsed && <span>Sign out</span>}
      </Button>
    </div>
  );
}
