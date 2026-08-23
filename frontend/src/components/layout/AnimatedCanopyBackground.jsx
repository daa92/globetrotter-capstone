/**
 * src/components/layout/AnimatedCanopyBackground.jsx
 *
 * The site's signature visual motif: a slow-drifting blend of three
 * radial gradients in the Cameroon-grounded palette (rainforest canopy
 * green, laterite red-clay, gold-hour light) — meant to evoke dappled
 * sunlight shifting through forest canopy, or heat-shimmer over
 * savanna at golden hour. Deliberately slow and ambient, not a
 * decoration competing with content.
 *
 * Pure CSS (background-position keyframes on layered radial-gradients),
 * no canvas/WebGL — cheap enough to run smoothly on a smart TV or a
 * budget phone, and prefers-reduced-motion freezes it to a static
 * gradient automatically (see index.css's global reduced-motion rule,
 * which zeroes animation-duration app-wide).
 *
 * Usage: render once, absolutely/fixed positioned behind content —
 * see Hero.jsx and DestinationDetail.jsx for examples. `fixed` keeps it
 * pinned to the viewport (good for a full-page ambient wash); pass
 * `variant="section"` for `absolute` instead, scoped to a parent with
 * `position: relative` (good for a hero band within a normal-scrolling
 * page).
 */
export default function AnimatedCanopyBackground({ variant = "fixed", className = "" }) {
  const position = variant === "fixed" ? "fixed" : "absolute";
  return (
    <div
      aria-hidden="true"
      className={`${position} inset-0 -z-10 overflow-hidden ${className}`}
      style={{ background: "#0B1A12" }}
    >
      <div className="canopy-glow canopy-glow-1" />
      <div className="canopy-glow canopy-glow-2" />
      <div className="canopy-glow canopy-glow-3" />
      {/* Subtle grain keeps the large soft gradients from banding/looking too "clean digital" — a tiny nod to texture over gloss. */}
      <div className="canopy-grain" />

      <style>{`
        .canopy-glow {
          position: absolute;
          border-radius: 9999px;
          filter: blur(60px);
          opacity: 0.55;
          will-change: transform;
        }
        .canopy-glow-1 {
          width: 60vmax; height: 60vmax;
          top: -15vmax; left: -10vmax;
          background: radial-gradient(circle, #1F7A4D 0%, transparent 70%);
          animation: canopyDrift1 34s ease-in-out infinite;
        }
        .canopy-glow-2 {
          width: 50vmax; height: 50vmax;
          bottom: -20vmax; right: -10vmax;
          background: radial-gradient(circle, #C1502E 0%, transparent 70%);
          animation: canopyDrift2 41s ease-in-out infinite;
        }
        .canopy-glow-3 {
          width: 40vmax; height: 40vmax;
          top: 30%; left: 50%;
          background: radial-gradient(circle, #E8B23D 0%, transparent 72%);
          opacity: 0.35;
          animation: canopyDrift3 28s ease-in-out infinite;
        }
        .canopy-grain {
          position: absolute; inset: 0;
          opacity: 0.05;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }
        @keyframes canopyDrift1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(8vmax, 6vmax) scale(1.15); }
        }
        @keyframes canopyDrift2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-6vmax, -8vmax) scale(1.1); }
        }
        @keyframes canopyDrift3 {
          0%, 100% { transform: translate(-50%, 0) scale(1); }
          50% { transform: translate(-50%, 4vmax) scale(1.2); }
        }
      `}</style>
    </div>
  );
}
