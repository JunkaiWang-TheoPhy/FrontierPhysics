"use client";

import { Button } from "@/components/ui/button";
import { DiscordIcon, FrontierPhysicsLogo } from "@/components/BrandIcon";
import { cn } from "@/lib/utils";
import { navItems, site } from "@/lib/site";
import { Github, Menu, Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useHydrated } from "@/lib/use-hydrated";

export function Navbar() {
  const { theme, setTheme } = useTheme();
  // next-themes only knows the resolved theme on the client, so the switcher
  // renders after hydration to avoid a server/client mismatch.
  const mounted = useHydrated();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [isScrollingDown, setIsScrollingDown] = useState(false);
  const lastScrollYRef = useRef(0);
  const pathname = usePathname();
  const shouldHideNavbar = isScrolled && isScrollingDown && !mobileMenuOpen;

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      setIsScrolled(currentScrollY > 50);
      setIsScrollingDown(
        currentScrollY > lastScrollYRef.current && currentScrollY > 8,
      );
      lastScrollYRef.current = currentScrollY;
    };

    lastScrollYRef.current = window.scrollY;
    window.addEventListener("scroll", handleScroll, { passive: true });
    // Navigating resets the scroll position without firing a scroll event, so
    // re-sync on the next frame — otherwise the bar can stay hidden after a
    // route change that happened mid-scroll.
    const frame = requestAnimationFrame(handleScroll);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [pathname]);

  return (
    <nav
      className={cn(
        "z-50 flex items-center justify-between px-4 py-2 transition-[opacity,filter,background-color,border-color] duration-300 ease-in-out",
        "fixed left-1/2 -translate-x-1/2 top-4",
        "w-[calc(100%-2rem)] max-w-5xl",
        "rounded-full border border-border",
        "bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60",
        shouldHideNavbar
          ? "opacity-0 blur-md pointer-events-none"
          : "opacity-100 blur-0",
      )}
    >
      <div className="flex items-center gap-2 font-bold hover:text-primary transition-colors">
        <Link href="/" className="flex items-center gap-2">
          {/* The mark's orbit fills two thirds of its box, so it needs a
              larger frame than the old icon to carry the same optical weight
              next to the wordmark. */}
          <FrontierPhysicsLogo className="w-7 h-7" />
          <span className="hidden sm:inline-block tracking-tight">
            {site.name}
          </span>
        </Link>
      </div>

      <ul className="hidden lg:flex items-center gap-1">
        {navItems.map((item) => {
          const className = cn(
            "text-sm font-medium transition-colors px-3 py-1.5 rounded-full hover:bg-muted/50",
            pathname === item.href
              ? "text-foreground"
              : "text-muted-foreground hover:text-foreground",
          );
          return (
            <li key={item.href}>
              {"external" in item && item.external ? (
                // Docs live in the repository, so this leaves the site rather
                // than routing to a mirrored copy.
                <a
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={className}
                >
                  {item.label}
                </a>
              ) : (
                <Link href={item.href} className={className}>
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ul>

      <div className="flex items-center gap-2 pl-2">
        {mounted && (
          <>
            <div className="hidden lg:flex items-center bg-muted/50 rounded-full border border-border/40 p-0.5">
              {[
                { name: "light", icon: Sun },
                { name: "dark", icon: Moon },
                { name: "system", icon: Monitor },
              ].map((mode) => (
                <Button
                  key={mode.name}
                  onClick={() => setTheme(mode.name)}
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-7 w-7",
                    theme === mode.name
                      ? "bg-background text-foreground hover:bg-background shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-transparent",
                  )}
                  aria-label={`Switch to ${mode.name} mode`}
                >
                  <mode.icon className="w-3.5 h-3.5" aria-hidden="true" />
                </Button>
              ))}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-8 w-8"
              onClick={() =>
                setTheme(
                  theme === "light"
                    ? "dark"
                    : theme === "dark"
                      ? "system"
                      : "light",
                )
              }
              aria-label="Toggle theme"
            >
              {theme === "light" ? (
                <Sun className="w-4 h-4" aria-hidden="true" />
              ) : theme === "dark" ? (
                <Moon className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Monitor className="w-4 h-4" aria-hidden="true" />
              )}
            </Button>
          </>
        )}

        <div className="flex items-center gap-1 border-l border-border/40 pl-2 ml-1">
          <Button
            variant="ghost"
            size="icon"
            asChild
            className="h-8 w-8"
            aria-label="Discord"
          >
            <a href={site.discord} target="_blank" rel="noopener noreferrer">
              <DiscordIcon className="w-4 h-4" aria-hidden="true" />
            </a>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            asChild
            className="h-8 w-8"
            aria-label="GitHub"
          >
            <a href={site.repo} target="_blank" rel="noopener noreferrer">
              <Github className="w-4 h-4" aria-hidden="true" />
            </a>
          </Button>
        </div>

        <div className="lg:hidden ml-1 relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label="Toggle menu"
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            <Menu className="w-4 h-4" aria-hidden="true" />
          </Button>
          {mobileMenuOpen && (
            <div className="absolute right-0 top-10 w-48 p-2 rounded-xl border border-border bg-popover text-popover-foreground shadow-lg">
              <div className="flex flex-col gap-1">
                {navItems.map((item) => {
                  const className =
                    "text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-3 py-2 rounded-lg hover:bg-muted/50";
                  const close = () => setMobileMenuOpen(false);
                  return "external" in item && item.external ? (
                    <a
                      key={item.href}
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={close}
                      className={className}
                    >
                      {item.label}
                    </a>
                  ) : (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={close}
                      className={className}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
