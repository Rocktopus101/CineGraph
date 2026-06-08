"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { isDevMode } from "@/lib/firebase";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Film } from "lucide-react";

const links = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/recommendations", label: "AI" },
  { href: "/analytics", label: "Analytics" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/lists", label: "Lists" },
  { href: "/reviews", label: "Reviews" },
];

export function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-primary">
          <Film className="h-6 w-6" />
          CineGraph
        </Link>
        <div className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm transition-colors hover:text-primary",
                pathname === l.href && "text-primary"
              )}
            >
              {l.label}
            </Link>
          ))}
          {user?.is_admin && (
            <>
              <Link href="/admin/ai" className={cn("rounded-md px-3 py-2 text-sm", pathname === "/admin/ai" && "text-primary")}>
                Admin
              </Link>
              <Link href="/eval" className={cn("rounded-md px-3 py-2 text-sm", pathname === "/eval" && "text-primary")}>
                Eval
              </Link>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          {user && (
            <Link href="/settings">
              <Button variant="ghost" size="sm">Settings</Button>
            </Link>
          )}
          {user ? (
            <Button variant="outline" size="sm" onClick={() => logout()}>
              Sign out
            </Button>
          ) : !isDevMode ? (
            <Link href="/login">
              <Button size="sm">Sign in</Button>
            </Link>
          ) : null}
        </div>
      </div>
    </nav>
  );
}
