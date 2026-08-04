"use client";

import { useEffect, useRef } from "react";
import "./Atoms.css";

interface AtomsProps {
  /** Stroke colour of the atoms and the bonds between them. */
  atomColor?: string;
  /** Seconds for one full revolution. */
  rotationPeriod?: number;
  /** Sphere radius as a fraction of the smaller viewport dimension. */
  radiusRatio?: number;
  className?: string;
}

/*
 * The atoms sit on a geodesic sphere and are bonded to their neighbours, so the
 * field reads as one large lattice turning in space rather than a flat drift.
 *
 * Vertices come from an icosahedron subdivided three times and pushed out to
 * the sphere: 642 evenly spaced points, every one equivalent to every other, which
 * is what keeps the mesh regular from any angle. Edges are the subdivided
 * triangle sides, deduplicated.
 *
 * Depth is carried by perspective scale and opacity alone — atoms at the back
 * are smaller and fainter — so the sphere reads as solid without any shading.
 *
 * The pointer curves the lattice: atoms near it fall inward and shrink as they
 * recede into the well, and because the bonds are drawn from the same displaced
 * positions the whole mesh dimples rather than just the dots — the rubber-sheet
 * picture of a mass curving spacetime, now wrapped onto the sphere.
 */
const SUBDIVISIONS = 3; // 3 → 642 vertices, 1920 bonds
const FOCAL = 2.6; // perspective strength, in sphere radii
const NEAR_ALPHA = 1;
const FAR_ALPHA = 0.25;
const TILT = -0.42; // radians; a slight lean so the poles are never edge-on

const WELL_RADIUS = 200; // px — scale over which curvature falls off
const WELL_PULL = 28; // px — deepest inward displacement
const WELL_SHRINK = 0.24; // how much an atom shrinks at the bottom of the well
const FOLLOW_EASE = 0.16; // how quickly the well tracks the pointer
const STRENGTH_EASE = 0.08; // how quickly it eases in and out

type Vec3 = [number, number, number];

/** An icosahedron subdivided `depth` times and normalised onto the unit sphere. */
function icosphere(depth: number): { vertices: Vec3[]; edges: [number, number][] } {
  const t = (1 + Math.sqrt(5)) / 2;
  const vertices: Vec3[] = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ];
  let faces: [number, number, number][] = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];

  const midpoints = new Map<string, number>();
  const midpoint = (a: number, b: number): number => {
    const key = a < b ? `${a}_${b}` : `${b}_${a}`;
    const cached = midpoints.get(key);
    if (cached !== undefined) return cached;
    const [ax, ay, az] = vertices[a];
    const [bx, by, bz] = vertices[b];
    vertices.push([(ax + bx) / 2, (ay + by) / 2, (az + bz) / 2]);
    const index = vertices.length - 1;
    midpoints.set(key, index);
    return index;
  };

  for (let i = 0; i < depth; i++) {
    const next: [number, number, number][] = [];
    for (const [a, b, c] of faces) {
      const ab = midpoint(a, b);
      const bc = midpoint(b, c);
      const ca = midpoint(c, a);
      next.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
    }
    faces = next;
  }

  // Push every vertex onto the unit sphere.
  const unit: Vec3[] = vertices.map(([x, y, z]) => {
    const length = Math.hypot(x, y, z) || 1;
    return [x / length, y / length, z / length];
  });

  const seen = new Set<string>();
  const edges: [number, number][] = [];
  for (const [a, b, c] of faces) {
    for (const [p, q] of [[a, b], [b, c], [c, a]] as [number, number][]) {
      const key = p < q ? `${p}_${q}` : `${q}_${p}`;
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push([p, q]);
    }
  }

  return { vertices: unit, edges };
}

/**
 * Renders one atom — a nucleus inside three orbital ellipses — into an
 * offscreen canvas, so the loop blits a sprite per vertex instead of
 * re-stroking three ellipses every frame.
 */
function createAtomSprite(
  color: string,
  size: number,
  dpr: number,
): HTMLCanvasElement {
  const sprite = document.createElement("canvas");
  sprite.width = size * dpr;
  sprite.height = size * dpr;

  const ctx = sprite.getContext("2d");
  if (!ctx) return sprite;

  ctx.scale(dpr, dpr);
  ctx.translate(size / 2, size / 2);
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1;

  const rx = size * 0.3;
  const ry = size * 0.125;

  for (const rotation of [0, Math.PI / 3, (2 * Math.PI) / 3]) {
    ctx.beginPath();
    ctx.ellipse(0, 0, rx, ry, rotation, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.arc(0, 0, size * 0.048, 0, Math.PI * 2);
  ctx.fill();

  return sprite;
}

const Atoms = ({
  atomColor = "#999",
  rotationPeriod = 90,
  radiusRatio = 0.94,
  className = "",
}: AtomsProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const requestRef = useRef<number | null>(null);
  const pointerRef = useRef({ x: 0, y: 0, inside: false });
  const wellRef = useRef({ x: 0, y: 0, strength: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Cap the ratio at 2 — beyond that the extra pixels cost more than the
    // sharpness is worth for a background this faint.
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const { vertices, edges } = icosphere(SUBDIVISIONS);
    const atomSize = 14;
    const sprite = createAtomSprite(atomColor, atomSize, dpr);
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    let width = 0;
    let height = 0;

    const resizeCanvas = () => {
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      // Draw in CSS pixels; the transform handles the device ratio.
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    const draw = (angle: number) => {
      ctx.clearRect(0, 0, width, height);

      const radius = Math.min(width, height) * radiusRatio;
      const cx = width / 2;
      const cy = height / 2;
      const sinY = Math.sin(angle);
      const cosY = Math.cos(angle);
      const sinX = Math.sin(TILT);
      const cosX = Math.cos(TILT);

      const well = wellRef.current;
      const curved = well.strength > 0.001;

      // Project every vertex once per frame, then reuse for bonds and atoms.
      const points = vertices.map(([x, y, z]) => {
        // Spin about the vertical axis, then lean the whole sphere forward.
        const rx = x * cosY + z * sinY;
        const rz = -x * sinY + z * cosY;
        const ry = y * cosX - rz * sinX;
        const rzz = y * sinX + rz * cosX;

        const scale = FOCAL / (FOCAL + rzz);
        // rzz spans [-1, 1]; map to a front-to-back opacity ramp.
        const depth = (rzz + 1) / 2;
        let px = cx + rx * radius * scale;
        let py = cy + ry * radius * scale;
        let sizeScale = scale;

        if (curved) {
          const dx = px - well.x;
          const dy = py - well.y;
          const distance = Math.hypot(dx, dy);
          // 1 at the centre of the well, decaying smoothly to 0 far away.
          const falling =
            ((WELL_RADIUS * WELL_RADIUS) /
              (distance * distance + WELL_RADIUS * WELL_RADIUS)) *
            well.strength;
          // Clamped so an atom is never dragged past the centre and inverted.
          const pull = Math.min(WELL_PULL * falling, distance * 0.8);
          if (distance > 0) {
            px -= (dx / distance) * pull;
            py -= (dy / distance) * pull;
          }
          sizeScale *= 1 - WELL_SHRINK * falling;
        }

        return {
          x: px,
          y: py,
          scale: sizeScale,
          alpha: NEAR_ALPHA + (FAR_ALPHA - NEAR_ALPHA) * depth,
        };
      });

      // Bonds first so the atoms always sit on top of them.
      ctx.strokeStyle = atomColor;
      ctx.lineWidth = 1;
      for (const [a, b] of edges) {
        const p = points[a];
        const q = points[b];
        ctx.globalAlpha = (p.alpha + q.alpha) / 2;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(q.x, q.y);
        ctx.stroke();
      }

      for (const p of points) {
        const size = atomSize * p.scale;
        ctx.globalAlpha = p.alpha;
        ctx.drawImage(sprite, p.x - size / 2, p.y - size / 2, size, size);
      }

      ctx.globalAlpha = 1;
    };

    const advanceWell = () => {
      const pointer = pointerRef.current;
      const well = wellRef.current;

      if (pointer.inside && well.strength < 0.001) {
        // Materialise where the pointer already is rather than sliding in from
        // wherever it was last seen.
        well.x = pointer.x;
        well.y = pointer.y;
      } else {
        well.x += (pointer.x - well.x) * FOLLOW_EASE;
        well.y += (pointer.y - well.y) * FOLLOW_EASE;
      }

      const target = pointer.inside ? 1 : 0;
      well.strength += (target - well.strength) * STRENGTH_EASE;
      if (!pointer.inside && well.strength < 0.001) well.strength = 0;
    };

    // Tracked on window, not the canvas: the hero's text and buttons sit above
    // the canvas and would otherwise swallow the pointer as it crosses them.
    const handleMouseMove = (event: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      pointerRef.current = {
        x,
        y,
        inside: x >= 0 && x <= rect.width && y >= 0 && y <= rect.height,
      };
    };

    const handleMouseLeave = () => {
      pointerRef.current.inside = false;
    };

    if (reduceMotion) {
      draw(0);
    } else {
      window.addEventListener("mousemove", handleMouseMove, { passive: true });
      document.addEventListener("mouseleave", handleMouseLeave);
      const started = performance.now();
      const tick = () => {
        const elapsed = (performance.now() - started) / 1000;
        advanceWell();
        draw((elapsed / rotationPeriod) * Math.PI * 2);
        requestRef.current = requestAnimationFrame(tick);
      };
      requestRef.current = requestAnimationFrame(tick);
    }

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [atomColor, rotationPeriod, radiusRatio]);

  return (
    <canvas ref={canvasRef} className={`atoms-canvas ${className}`}></canvas>
  );
};

export default Atoms;
