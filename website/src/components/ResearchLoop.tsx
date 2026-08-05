/**
 * Circular "research iteration loop" figure: three wide arc arrows
 * (research -> implement -> evaluate) chasing each other clockwise.
 * Pure inline SVG so it inherits the site font and needs no assets.
 */
export function ResearchLoop({ className }: { className?: string }) {
  return (
    <svg
      viewBox="150 95 600 600"
      role="img"
      aria-label="Research iteration loop: Research & Plan, Implement & Experiment, Evaluate & Feedback"
      className={className}
    >
      <defs>
        {/* Invisible guides the curved labels ride on (bottom two reversed so text stays upright). */}
        <path id="rl-g1" d="M289.5,234.5 A227,227 0 0 1 613.3,237.3" fill="none" />
        <path id="rl-g2" d="M309.3,254.3 A199,199 0 0 1 593.2,256.8" fill="none" />
        <path id="rl-o1" d="M487.3,606.7 A215,215 0 0 0 652.0,321.5" fill="none" />
        <path id="rl-o2" d="M492.2,634.3 A243,243 0 0 0 678.4,311.9" fill="none" />
        <path id="rl-p1" d="M250.7,314.5 A215,215 0 0 0 405.3,605.3" fill="none" />
        <path id="rl-p2" d="M224.7,304.0 A243,243 0 0 0 399.5,632.7" fill="none" />
      </defs>

      {/* Research & Plan (green, top) */}
      <path
        fill="#dfede5"
        d="M227.2,239.0 A272,272 0 0 1 613.7,177.8
           L622.1,166.6 L643.3,287.9 L543.9,270.4 L552.3,259.2
           A170,170 0 0 0 310.7,297.5 Z"
      />
      {/* Implement & Experiment (orange, bottom right) */}
      <path
        fill="#fbe8cd"
        d="M696.5,280.1 A272,272 0 0 1 556.3,645.4
           L561.8,658.3 L446.1,616.0 L511.0,538.6 L516.4,551.5
           A170,170 0 0 0 604.1,323.2 Z"
      />
      {/* Evaluate & Feedback (purple, bottom left) */}
      <path
        fill="#ded8ec"
        d="M426.3,666.0 A272,272 0 0 1 180.0,361.9
           L166.1,360.2 L260.6,281.2 L295.2,376.0 L281.3,374.3
           A170,170 0 0 0 435.2,564.4 Z"
      />

      {/* Labels inside the arrows, two lines each */}
      <g fontSize="26" fontWeight="700" letterSpacing="0.3">
        <g fill="#24523f">
          <text>
            <textPath href="#rl-g1" startOffset="50%" textAnchor="middle">
              Research &amp;
            </textPath>
          </text>
          <text>
            <textPath href="#rl-g2" startOffset="50%" textAnchor="middle">
              Plan
            </textPath>
          </text>
        </g>
        <g fill="#7a4a10">
          <text>
            <textPath href="#rl-o1" startOffset="50%" textAnchor="middle">
              Implement &amp;
            </textPath>
          </text>
          <text>
            <textPath href="#rl-o2" startOffset="50%" textAnchor="middle">
              Experiment
            </textPath>
          </text>
        </g>
        <g fill="#453766">
          <text>
            <textPath href="#rl-p1" startOffset="50%" textAnchor="middle">
              Evaluate &amp;
            </textPath>
          </text>
          <text>
            <textPath href="#rl-p2" startOffset="50%" textAnchor="middle">
              Feedback
            </textPath>
          </text>
        </g>
      </g>
    </svg>
  );
}
