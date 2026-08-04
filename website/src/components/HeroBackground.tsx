"use client";

import Atoms from "@/components/Atoms";
import { useHydrated } from "@/lib/use-hydrated";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function HeroBackground() {
  const hydrated = useHydrated();
  const { theme, resolvedTheme } = useTheme();
  const [atomColor, setAtomColor] = useState("");

  useEffect(() => {
    const updateColors = () => {
      const style = getComputedStyle(document.documentElement);
      const foreground = style.getPropertyValue("--foreground") || "#000";

      // Atoms are the foreground colour at very low opacity so they stay
      // legible on both the light and the dark background without competing
      // with the headline.
      const transparency = resolvedTheme === "dark" ? "80%" : "90%";

      setAtomColor(
        `color-mix(in srgb, ${foreground}, transparent ${transparency})`,
      );
    };

    // Read the computed styles a frame after the theme class lands on <html>,
    // otherwise the canvas picks up the colours of the outgoing theme.
    const frame = requestAnimationFrame(updateColors);
    return () => cancelAnimationFrame(frame);
  }, [resolvedTheme, theme]);

  if (!hydrated) {
    return (
      <div className="absolute inset-0 w-full h-full -z-50 bg-background" />
    );
  }

  return (
    <div className="absolute inset-0 w-full h-full -z-50 bg-background">
      <Atoms atomColor={atomColor} />
      {/* Vignette so the field fades out towards the edges of the hero. */}
      <div className="absolute inset-0 w-full h-full pointer-events-none bg-[radial-gradient(circle_at_center,transparent_40%,var(--background)_100%)] opacity-60" />
      <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}
