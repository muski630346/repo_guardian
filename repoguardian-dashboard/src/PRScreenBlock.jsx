import { useEffect } from "react";

// ─── TOKENS ──────────────────────────────────────────────────────────────────
const C = {
  bg:       "#0d1117",
  surface:  "#161b22",
  surface2: "#21262d",
  border:   "#30363d",
  text:     "#e6edf3",
  textMid:  "#8b949e",
  textDim:  "#484f58",
  red:      "#f85149",
  orange:   "#fb8500",
  green:    "#3fb950",
  blue:     "#388bfd",
  yellow:   "#e3b341",
  purple:   "#a371f7",
};

// ─── KEYFRAMES ───────────────────────────────────────────────────────────────
const KEYFRAMES = `
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Fira+Code:wght@400;500;600;700&display=swap');
  @keyframes prbFadeIn    { from{opacity:0} to{opacity:1} }
  @keyframes prbSlideUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
  @keyframes prbItemIn    { from{opacity:0;transform:translateX(-10px)} to{opacity:1;transform:translateX(0)} }
  @keyframes prbStatPop   { from{opacity:0;transform:scale(.55)} to{opacity:1;transform:scale(1)} }
  @keyframes prbOctoFloat {
    0%,100%{transform:translateY(0) rotate(0deg)}
    30%    {transform:translateY(-6px) rotate(-5deg)}
    65%    {transform:translateY(-2px) rotate(3deg)}
  }
  @keyframes prbRingPulse {
    0%,100%{box-shadow:0 0 0 0 rgba(248,81,73,.55),0 0 0 0 rgba(248,81,73,.2)}
    50%    {box-shadow:0 0 0 22px rgba(248,81,73,0),0 0 0 44px rgba(248,81,73,0)}
  }
  @keyframes prbShake {
    0%,100%{transform:translateX(0)}
    20%    {transform:translateX(-7px)}
    40%    {transform:translateX(7px)}
    60%    {transform:translateX(-4px)}
    80%    {transform:translateX(4px)}
  }
  @keyframes prbScan {
    0%  {top:-2px}
    100%{top:102%}
  }
  @keyframes prbDotPulse {
    0%,100%{box-shadow:0 0 0 0 currentColor}
    50%    {box-shadow:0 0 0 5px transparent}
  }
`;

function useInjectKeyframes() {
  useEffect(() => {
    const id = "prb-keyframes";
    if (!document.getElementById(id)) {
      const el = document.createElement("style");
      el.id = id;
      el.textContent = KEYFRAMES;
      document.head.appendChild(el);
    }
  }, []);
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const scoreColor   = (s) => (s >= 80 ? C.green : s >= 60 ? C.orange : C.red);
const avatarPalette = [C.blue, C.green, C.purple, C.orange, C.red, C.yellow];
const avatarColor   = (name) => avatarPalette[name.charCodeAt(0) % avatarPalette.length];

// ─── ATOMS ───────────────────────────────────────────────────────────────────
function OctocatSVG({ size = 80, color = C.red }) {
  return (
    <svg width={size} height={size} viewBox="0 0 98 96" fill={color}
      xmlns="http://www.w3.org/2000/svg"
      style={{ filter: `drop-shadow(0 0 16px ${color}90)` }}>
      <path fillRule="evenodd" clipRule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993
        40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59
        2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015
        4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178
        1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778
        5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1
        12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67
        6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404
        23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0
        1.304.89 2.853 3.316 2.364C84.003 89.39 97.707 71 97.707 49.217 97.707 22 75.788 0 48.854 0z"/>
    </svg>
  );
}

function PRIcon({ color = C.red, size = 13 }) {
  return (
    <svg width={size} height={size} fill={color} viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
      <path d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177
        3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0
        113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0
        011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0
        01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
    </svg>
  );
}

function CloseIcon({ size = 12, color = C.red }) {
  return (
    <svg width={size} height={size} fill={color} viewBox="0 0 16 16">
      <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06
        8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94
        8 3.72 4.78a.75.75 0 010-1.06z"/>
    </svg>
  );
}

function Avatar({ name, size = 26 }) {
  const bg = avatarColor(name);
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: `linear-gradient(135deg, ${bg}cc, ${bg}44)`,
      border: `1.5px solid ${bg}55`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.38, fontWeight: 700, color: "#fff",
      fontFamily: "'Fira Code', monospace",
    }}>
      {name[0].toUpperCase()}
    </div>
  );
}

function StatusDot({ color, pulse = false }) {
  return (
    <span style={{
      display: "inline-block", width: 7, height: 7,
      borderRadius: "50%", background: color, flexShrink: 0,
      boxShadow: `0 0 0 3px ${color}25`,
      animation: pulse ? "prbDotPulse 2.4s ease-in-out infinite" : "none",
    }} />
  );
}

function Pill({ children, color }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "4px 11px", borderRadius: 20,
      background: `${color}12`, border: `1px solid ${color}38`,
      fontSize: 11, fontWeight: 600, color,
      fontFamily: "'Fira Code', monospace", whiteSpace: "nowrap",
    }}>
      {children}
    </span>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
/**
 * PRScreenBlock
 *
 * Props:
 *   open      {number}   — current open PR count (from API)
 *   limit     {number}   — configured max allowed (from API)
 *   prs       {Array}    — list of open PRs [{id, author, branch, score, grade}]
 *   visible   {boolean}  — whether to show the blocker
 *   onDismiss {function} — callback when user clicks Dismiss
 */
export function PRScreenBlock({ open = 0, limit = 5, prs = [], visible = false, onDismiss }) {
  useInjectKeyframes();

  const overBy    = Math.max(0, open - limit);
  const displayed = prs.slice(0, 5);

  if (!visible) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      background: "rgba(13,17,23,.97)",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      overflow: "hidden",
      fontFamily: "'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif",
      animation: "prbFadeIn .3s ease both",
    }}>

      {/* dot-grid texture */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage:
          "linear-gradient(rgba(48,54,61,.13) 1px, transparent 1px)," +
          "linear-gradient(90deg, rgba(48,54,61,.13) 1px, transparent 1px)",
        backgroundSize: "36px 36px",
      }} />

      {/* animated red scan line */}
      <div style={{
        position: "absolute", left: 0, right: 0, height: 2,
        pointerEvents: "none",
        background: "linear-gradient(90deg, transparent, rgba(248,81,73,.5), transparent)",
        animation: "prbScan 2.8s linear infinite",
      }} />

      {/* content column */}
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        position: "relative", zIndex: 1,
        animation: "prbSlideUp .4s cubic-bezier(.16,1,.3,1) both",
        padding: "0 24px", width: "100%", maxWidth: 480,
      }}>

        {/* Octocat circle */}
        <div style={{
          width: 168, height: 168, borderRadius: "50%",
          background: "rgba(248,81,73,.07)",
          border: "2.5px solid rgba(248,81,73,.55)",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 28, flexShrink: 0, position: "relative",
          animation: "prbRingPulse 2.6s ease-in-out infinite, prbOctoFloat 5s ease-in-out infinite, prbShake .5s .05s ease",
        }}>
          <div style={{ position: "absolute", inset: -13, borderRadius: "50%", border: "1px solid rgba(248,81,73,.16)", pointerEvents: "none" }} />
          <div style={{ position: "absolute", inset: -27, borderRadius: "50%", border: "1px solid rgba(248,81,73,.07)", pointerEvents: "none" }} />
          <OctocatSVG size={92} color={C.red} />
        </div>

        {/* eyebrow */}
        <p style={{
          fontSize: 10, letterSpacing: "3px", color: "rgba(248,81,73,.75)",
          fontFamily: "'Fira Code', monospace", fontWeight: 700,
          textTransform: "uppercase", marginBottom: 10,
        }}>
          Action blocked
        </p>

        {/* title */}
        <h1 style={{
          fontSize: 26, fontWeight: 800, color: "#f0f6fc",
          letterSpacing: "-.6px", marginBottom: 10, textAlign: "center",
          lineHeight: 1.1,
        }}>
          PR limit exceeded
        </h1>

        {/* subtitle */}
        <p style={{
          fontSize: 13, color: C.textMid, textAlign: "center",
          maxWidth: 360, lineHeight: 1.7, marginBottom: 26,
          fontFamily: "'Fira Code', monospace",
        }}>
          This repo has{" "}
          <span style={{ color: C.red, fontWeight: 700 }}>{open} open PRs</span>
          {" "}against a limit of{" "}
          <span style={{ color: C.orange, fontWeight: 700 }}>{limit}</span>.
          {" "}Merge or close{" "}
          <span style={{ color: C.yellow, fontWeight: 700 }}>
            {overBy} PR{overBy !== 1 ? "s" : ""}
          </span>
          {" "}to unblock new submissions.
        </p>

        {/* stats row */}
        <div style={{ display: "flex", alignItems: "center", gap: 28, marginBottom: 24 }}>
          {[
            { label: "Open PRs", value: open,          color: C.red    },
            { label: "Limit",    value: limit,          color: C.orange },
            { label: "Over by",  value: `+${overBy}`,  color: C.yellow },
          ].map(({ label, value, color }, i) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{
                fontSize: 30, fontWeight: 800, color, lineHeight: 1,
                fontFamily: "'Fira Code', monospace",
                textShadow: `0 0 24px ${color}55`,
                animation: `prbStatPop .5s ${i * .09}s cubic-bezier(.34,1.56,.64,1) both`,
              }}>{value}</div>
              <div style={{
                fontSize: 9, color: C.textDim, letterSpacing: "1.5px",
                textTransform: "uppercase", marginTop: 5,
                fontFamily: "'Fira Code', monospace",
              }}>{label}</div>
            </div>
          ))}
        </div>

        {/* divider */}
        <div style={{
          width: 240, height: 1, marginBottom: 20,
          background: "linear-gradient(90deg, transparent, rgba(248,81,73,.3), transparent)",
        }} />

        {/* open PR list */}
        {displayed.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%", marginBottom: 26 }}>
            {displayed.map((r, i) => {
              const sc = scoreColor(r.score);
              return (
                <div key={r.id ?? r.pr} style={{
                  display: "flex", alignItems: "center", gap: 11,
                  background: "rgba(248,81,73,.05)",
                  border: "1px solid rgba(248,81,73,.2)",
                  borderRadius: 9, padding: "10px 14px",
                  animation: `prbItemIn .3s ${i * .07}s ease both`,
                  transition: "background .15s", cursor: "default",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(248,81,73,.1)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(248,81,73,.05)"}
                >
                  <PRIcon color={C.red} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: C.red, fontFamily: "'Fira Code', monospace", minWidth: 38 }}>
                    #{r.id ?? r.pr}
                  </span>
                  <Avatar name={r.author || "?"} size={24} />
                  <span style={{ fontSize: 11, color: C.textMid, fontFamily: "'Fira Code', monospace", minWidth: 56 }}>
                    @{r.author}
                  </span>
                  <span style={{ fontSize: 11, color: C.textDim, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "'Fira Code', monospace" }}>
                    {r.branch}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: sc, fontFamily: "'Fira Code', monospace", textShadow: `0 0 8px ${sc}70` }}>
                    {r.score}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* dismiss */}
        <button onClick={onDismiss} style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "11px 26px", borderRadius: 9,
          background: "rgba(248,81,73,.1)", border: "1px solid rgba(248,81,73,.38)",
          color: C.red, fontSize: 13, fontWeight: 700,
          cursor: "pointer", outline: "none",
          fontFamily: "'Fira Code', monospace",
          letterSpacing: ".4px", transition: "background .15s",
        }}
        onMouseEnter={e => e.currentTarget.style.background = "rgba(248,81,73,.2)"}
        onMouseLeave={e => e.currentTarget.style.background = "rgba(248,81,73,.1)"}
        >
          <CloseIcon />
          Dismiss &amp; manage open PRs
        </button>
      </div>
    </div>
  );
}

export default PRScreenBlock;