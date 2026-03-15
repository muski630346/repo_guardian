import { useState, useEffect, useRef, useContext, createContext } from "react";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";
import { PRScreenBlock } from "./PRScreenBlock";

/* ─── API URL — backend running on port 8000 ─────────────────────────────── */
const API = "http://localhost:8000";

/* ─── Theme tokens ───────────────────────────────────────────────────────── */
export const ThemeContext = createContext();
export const useTheme = () => useContext(ThemeContext);

export const DARK = {
  bg:          "#0d1117",
  bgCard:      "#161b22",
  bgSubtle:    "rgba(255,255,255,0.03)",
  bgInput:     "rgba(255,255,255,0.04)",
  bgInputAlt:  "rgba(255,255,255,0.06)",
  border:      "rgba(255,255,255,0.08)",
  borderFaint: "rgba(255,255,255,0.04)",
  borderHover: "rgba(59,130,246,0.35)",
  nav:         "#0d1117",
  navBorder:   "rgba(255,255,255,0.08)",
  text:        "#e2e8f0",
  textHeading: "#f1f5f9",
  textMuted:   "#64748b",
  textSub:     "#94a3b8",
  textFaint:   "#475569",
  textDim:     "#374151",
  gridStroke:  "rgba(255,255,255,0.04)",
  polarGrid:   "rgba(255,255,255,0.07)",
  scrollThumb: "rgba(255,255,255,0.1)",
  tipBg:       "#1a2035",
  tipBorder:   "rgba(255,255,255,0.1)",
  fixBg:       "rgba(34,197,94,0.06)",
  fixBorder:   "rgba(34,197,94,0.14)",
  errBg:       "rgba(239,68,68,0.08)",
  errBorder:   "rgba(239,68,68,0.2)",
  tooltipRect: "#0d1117",
  isDark:      true,
};

export const LIGHT = {
  bg:          "#f1f5f9",
  bgCard:      "#ffffff",
  bgSubtle:    "rgba(0,0,0,0.02)",
  bgInput:     "rgba(0,0,0,0.04)",
  bgInputAlt:  "rgba(0,0,0,0.06)",
  border:      "rgba(0,0,0,0.08)",
  borderFaint: "rgba(0,0,0,0.05)",
  borderHover: "rgba(59,130,246,0.5)",
  nav:         "#ffffff",
  navBorder:   "rgba(0,0,0,0.08)",
  text:        "#1e293b",
  textHeading: "#0f172a",
  textMuted:   "#64748b",
  textSub:     "#475569",
  textFaint:   "#64748b",
  textDim:     "#94a3b8",
  gridStroke:  "rgba(0,0,0,0.05)",
  polarGrid:   "rgba(0,0,0,0.1)",
  scrollThumb: "rgba(0,0,0,0.15)",
  tipBg:       "#ffffff",
  tipBorder:   "rgba(0,0,0,0.12)",
  fixBg:       "rgba(34,197,94,0.07)",
  fixBorder:   "rgba(34,197,94,0.2)",
  errBg:       "rgba(239,68,68,0.06)",
  errBorder:   "rgba(239,68,68,0.2)",
  tooltipRect: "#f8fafc",
  isDark:      false,
};

function ThemeToggle({ dark, onToggle }) {
  return (
    <button onClick={onToggle}
      title={dark ? "Switch to day mode" : "Switch to night mode"}
      style={{
        display:"flex", alignItems:"center", gap:8,
        background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
        border: `1px solid ${dark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.1)"}`,
        borderRadius:20, padding:"5px 12px", cursor:"pointer",
        transition:"all 0.25s",
        color: dark ? "#94a3b8" : "#475569",
        fontSize:12, fontWeight:600,
      }}
    >
      <div style={{
        width:36, height:20, borderRadius:10, position:"relative",
        background: dark ? "#3b82f6" : "#cbd5e1",
        transition:"background 0.3s", flexShrink:0,
      }}>
        <div style={{
          position:"absolute", top:3,
          left: dark ? 19 : 3,
          width:14, height:14, borderRadius:"50%", background:"#fff",
          boxShadow:"0 1px 3px rgba(0,0,0,0.3)",
          transition:"left 0.3s",
        }}/>
      </div>
      <span>{dark ? "🌙 Night" : "☀️ Day"}</span>
    </button>
  );
}


/* ─── FALLBACK empty state (shown while loading) ─────────────────────────── */
const EMPTY = {
  pull_requests: [],
  health_trend:  [],
  issues_per_pr: [],
  findings:      [],
  agents_data:   [],
  pie_data:      [],
  radar_data:    [],
  live_log:      [],
  stats: { total_prs: 0, total_findings: 0, avg_score: 0, critical_count: 0 },
};

const AGENT_FILTER_MAP = {
  "Security":"Security Agent","Dependency":"Dependency Agent",
  "Review":"PR Review Agent",
};

const SEV_CFG = {
  CRITICAL:{color:"#ef4444",bg:"rgba(239,68,68,0.12)",  border:"rgba(239,68,68,0.3)"  },
  HIGH:    {color:"#f97316",bg:"rgba(249,115,22,0.12)", border:"rgba(249,115,22,0.3)" },
  MEDIUM:  {color:"#eab308",bg:"rgba(234,179,8,0.12)",  border:"rgba(234,179,8,0.3)"  },
  LOW:     {color:"#6b7280",bg:"rgba(107,114,128,0.1)", border:"rgba(107,114,128,0.25)"},
};

const VERDICT_CFG = {
  "Approved":  {color:"#22c55e",bg:"rgba(34,197,94,0.1)",  border:"rgba(34,197,94,0.3)",  icon:"✓"},
  "Needs Work":{color:"#f97316",bg:"rgba(249,115,22,0.1)", border:"rgba(249,115,22,0.3)", icon:"⚠"},
  "Rejected":  {color:"#ef4444",bg:"rgba(239,68,68,0.1)",  border:"rgba(239,68,68,0.3)",  icon:"✗"},
};

/* ─── ANIMATED NUMBER ────────────────────────────────────────────────────── */
function AnimNum({ value }) {
  const [n, setN] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    ref.current = null;
    const step = ts => {
      if (!ref.current) ref.current = ts;
      const p = Math.min((ts - ref.current) / 1200, 1);
      setN(Math.round((1 - Math.pow(1 - p, 3)) * value));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [value]);
  return <>{n}</>;
}

/* ─── SCORE RING ─────────────────────────────────────────────────────────── */
function ScoreRing({ score, size = 110 }) {
  const r = size / 2 - 9;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  return (
    <div style={{ position:"relative", width:size, height:size, flexShrink:0 }}>
      <svg width={size} height={size} style={{ transform:"rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={7} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#22c55e" strokeWidth={7}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{transition:"stroke-dashoffset 1.5s cubic-bezier(.34,1.56,.64,1)",filter:"drop-shadow(0 0 6px #22c55e)"}}
        />
      </svg>
      <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center"}}>
        <span style={{fontSize:size*0.27,fontWeight:800,color:"#22c55e",fontFamily:"monospace"}}>{score}</span>
      </div>
    </div>
  );
}

/* ─── SMALL COMPONENTS ───────────────────────────────────────────────────── */
function VerdictBadge({ v }) {
  const c = VERDICT_CFG[v] || VERDICT_CFG["Needs Work"];
  return <span style={{fontSize:11,fontWeight:700,padding:"3px 10px",borderRadius:5,background:c.bg,color:c.color,border:`1px solid ${c.border}`}}>{c.icon} {v}</span>;
}

function SevBadge({ sev }) {
  const c = SEV_CFG[sev] || SEV_CFG.LOW;
  return <span style={{fontSize:10,fontWeight:800,padding:"2px 8px",borderRadius:4,background:c.bg,color:c.color,border:`1px solid ${c.border}`,letterSpacing:0.5}}>{sev}</span>;
}

function AgentBadge({ name }) {
  return <span style={{fontSize:10,fontWeight:700,padding:"2px 8px",borderRadius:4,background:"rgba(139,92,246,0.15)",color:"#a78bfa",border:"1px solid rgba(139,92,246,0.3)",letterSpacing:0.5}}>{name}</span>;
}

function DarkTip({ active, payload, label }) {
  const T = useTheme();
  if (!active || !payload?.length) return null;
  return (
    <div style={{background:T.tipBg,border:`1px solid ${T.tipBorder}`,borderRadius:8,padding:"10px 14px",fontSize:12,boxShadow:"0 4px 16px rgba(0,0,0,0.15)"}}>
      <div style={{color:T.textSub,marginBottom:5,fontWeight:600}}>{label}</div>
      {payload.map((p,i) => (
        <div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
          <span style={{width:8,height:8,borderRadius:2,background:p.color,display:"inline-block"}}/>
          <span style={{color:T.textSub}}>{p.name}:</span>
          <span style={{color:T.textHeading,fontWeight:700}}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  const T = useTheme();
  return (
    <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"20px 22px",transition:"transform 0.2s, background 0.3s",cursor:"default"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:14}}>
        <div style={{width:38,height:38,borderRadius:9,background:T.bgInput,display:"flex",alignItems:"center",justifyContent:"center",fontSize:17,color:T.textSub}}>{icon}</div>
        <span style={{color:"#22c55e",fontSize:16}}>↗</span>
      </div>
      <div style={{fontSize:38,fontWeight:800,color,fontFamily:"monospace",lineHeight:1,marginBottom:6}}><AnimNum value={value} /></div>
      <div style={{fontSize:13,color:T.textMuted}}>{label}</div>
    </div>
  );
}


/* ══════════════ WAVY DOT HEALTH TREND ══════════════════════════════════ */
function WavyHealthTrend({ data }) {
  const T = useTheme();
  const [hovered, setHovered]   = useState(null);
  const [animated, setAnimated] = useState(false);
  const [lineLen,  setLineLen]  = useState(0);
  const pathRef  = useRef(null);
  const timerRef = useRef(null);

  // Last 5 PRs only
  const pts_raw = data.slice(-5);

  useEffect(() => {
    setAnimated(false);
    setLineLen(0);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setAnimated(true);
      if (pathRef.current) {
        const len = pathRef.current.getTotalLength();
        setLineLen(len);
      }
    }, 120);
    return () => clearTimeout(timerRef.current);
  }, [JSON.stringify(pts_raw.map(d=>d.score))]);

  const W = 580, H = 260, PADL = 44, PADR = 24, PADT = 48, PADB = 50;
  const usableW = W - PADL - PADR;
  const usableH = H - PADT - PADB;

  const points = pts_raw.map((d, i) => {
    const x = PADL + (pts_raw.length === 1 ? usableW/2 : (i / (pts_raw.length - 1)) * usableW);
    const y = PADT + (1 - d.score / 100) * usableH;
    return { x, y, score: d.score, name: d.name };
  });

  // Catmull-Rom → cubic bezier for extra smoothness
  const smooth = (pts) => {
    if (pts.length < 2) return "";
    const d = [`M ${pts[0].x} ${pts[0].y}`];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(i-1, 0)];
      const p1 = pts[i];
      const p2 = pts[i+1];
      const p3 = pts[Math.min(i+2, pts.length-1)];
      const tension = 0.4;
      const cp1x = p1.x + (p2.x - p0.x) * tension;
      const cp1y = p1.y + (p2.y - p0.y) * tension;
      const cp2x = p2.x - (p3.x - p1.x) * tension;
      const cp2y = p2.y - (p3.y - p1.y) * tension;
      d.push(`C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`);
    }
    return d.join(" ");
  };

  const pathD = smooth(points);
  const last  = points[points.length - 1];
  const areaD = pathD && last
    ? pathD + ` L ${last.x} ${PADT+usableH} L ${points[0].x} ${PADT+usableH} Z`
    : "";

  const dotColor = (s) => s >= 85 ? "#22c55e" : s >= 65 ? "#3b82f6" : "#ef4444";
  const scoreGrade = (s) => s >= 85 ? "A" : s >= 65 ? "B" : s >= 50 ? "C" : "F";

  const yLines = [0, 25, 50, 75, 100];
  const totalLen = lineLen || 800;

  return (
    <div style={{
      background:T.bgCard,
      border:`1px solid ${T.border}`,
      borderRadius:14,
      padding:"22px 24px",
      position:"relative",
      overflow:"hidden",
      transition:"background 0.3s",
    }}>
      {/* Background grid glow */}
      <div style={{
        position:"absolute",bottom:-60,left:-60,width:300,height:300,
        background:"radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 65%)",
        pointerEvents:"none",
      }}/>

      {/* Header */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:8,position:"relative"}}>
        <div style={{display:"flex",alignItems:"center",gap:9}}>
          <div style={{
            width:28,height:28,borderRadius:8,
            background:"linear-gradient(135deg,rgba(59,130,246,0.25),rgba(99,102,241,0.15))",
            border:"1px solid rgba(59,130,246,0.3)",
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:13,
          }}>〜</div>
          <div>
            <div style={{fontWeight:700,fontSize:15,color:"#f1f5f9"}}>Repo Health Trend</div>
            <div style={{fontSize:10,color:"#475569",marginTop:1}}>Last {pts_raw.length} pull request{pts_raw.length!==1?"s":""}</div>
          </div>
        </div>

        {pts_raw.length > 0 && (
          <div style={{display:"flex",gap:14,alignItems:"center"}}>
            {[["#22c55e","A","≥85"],["#3b82f6","B","65–84"],["#ef4444","F","<65"]].map(([c,g,l])=>(
              <div key={g} style={{display:"flex",alignItems:"center",gap:5,fontSize:11,color:"#64748b"}}>
                <div style={{width:8,height:8,borderRadius:"50%",background:c,boxShadow:`0 0 4px ${c}88`}}/>
                <span style={{color:"#475569"}}>{g}</span>
                <span style={{color:"#374151",fontSize:10}}>{l}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {pts_raw.length === 0 ? (
        <div style={{
          display:"flex",flexDirection:"column",alignItems:"center",
          justifyContent:"center",padding:"60px 0",gap:14,
        }}>
          <div style={{display:"flex",gap:8}}>
            {[0,1,2,3,4].map(i=>(
              <div key={i} style={{
                width:10,height:10,borderRadius:"50%",
                background:"rgba(59,130,246,0.2)",
                border:"1px solid rgba(59,130,246,0.35)",
                animation:"pulse 1.8s ease-in-out infinite",
                animationDelay:`${i*0.18}s`,
              }}/>
            ))}
          </div>
          <div style={{fontSize:13,color:"#374151"}}>No PR data yet — run the orchestrator first</div>
        </div>
      ) : (
        <div style={{position:"relative",width:"100%"}}>
          <svg
            width="100%" height={H}
            viewBox={`0 0 ${W} ${H}`}
            style={{overflow:"visible",display:"block"}}
          >
            <defs>
              {/* Multi-stop gradient area fill */}
              <linearGradient id="wg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#3b82f6" stopOpacity="0.22"/>
                <stop offset="60%"  stopColor="#6366f1" stopOpacity="0.08"/>
                <stop offset="100%" stopColor="#3b82f6" stopOpacity="0"/>
              </linearGradient>

              {/* Glow filter for dots */}
              <filter id="dotGlow" x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="4" result="blur"/>
                <feMerge>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>

              {/* Glow filter for line */}
              <filter id="lineGlow" x="-5%" y="-40%" width="110%" height="180%">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>

              {/* Clip the draw-on animation */}
              <clipPath id="lineClip">
                <rect
                  x={0} y={0} width={animated ? W : 0} height={H}
                  style={{transition:`width ${pts_raw.length * 0.35 + 0.4}s cubic-bezier(0.4,0,0.2,1) 0.2s`}}
                />
              </clipPath>
            </defs>

            {/* Horizontal grid lines with labels */}
            {yLines.map(v => {
              const y = PADT + (1 - v/100) * usableH;
              return (
                <g key={v}>
                  <line
                    x1={PADL} y1={y} x2={W-PADR} y2={y}
                    stroke={v === 50 ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.035)"}
                    strokeWidth={v===50?1:0.7}
                    strokeDasharray={v===50?"":"4 6"}
                  />
                  <text
                    x={PADL-10} y={y+4}
                    textAnchor="end"
                    fill={v===50?T.textFaint:T.textDim}
                    fontSize={11}
                    fontWeight={v===50?"600":"400"}
                    fontFamily="monospace"
                  >{v}</text>
                </g>
              );
            })}

            {/* Vertical drop lines from dots */}
            {points.map((pt, i) => (
              <line
                key={`vl-${i}`}
                x1={pt.x} y1={pt.y + 8}
                x2={pt.x} y2={PADT + usableH}
                stroke={`${dotColor(pt.score)}18`}
                strokeWidth={1}
                strokeDasharray="3 5"
                style={{
                  opacity: animated ? 1 : 0,
                  transition: `opacity 0.4s ease ${0.6 + i*0.12}s`,
                }}
              />
            ))}

            {/* Area fill — clipped draw-on */}
            {areaD && (
              <path
                d={areaD}
                fill="url(#wg)"
                clipPath="url(#lineClip)"
                style={{opacity: animated ? 1 : 0, transition:"opacity 0.5s ease 0.3s"}}
              />
            )}

            {/* Wave line — draw-on with clip */}
            {pathD && (
              <g filter="url(#lineGlow)" clipPath="url(#lineClip)">
                {/* Thick glow underneath */}
                <path
                  d={pathD} fill="none"
                  stroke="rgba(99,102,241,0.25)"
                  strokeWidth={6}
                  strokeLinecap="round"
                />
                {/* Sharp main line */}
                <path
                  ref={pathRef}
                  d={pathD} fill="none"
                  stroke="url(#lineStroke)"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                />
              </g>
            )}

            {/* Line gradient (horizontal) */}
            <defs>
              <linearGradient id="lineStroke" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%"   stopColor="#6366f1"/>
                <stop offset="50%"  stopColor="#3b82f6"/>
                <stop offset="100%" stopColor="#22c55e"/>
              </linearGradient>
            </defs>

            {/* Dots — staggered bounce-in */}
            {points.map((pt, i) => {
              const c   = dotColor(pt.score);
              const isH = hovered === i;
              const delay = `${0.35 + i * 0.14}s`;

              return (
                <g
                  key={`dot-${i}`}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                  style={{cursor:"pointer"}}
                >
                  {/* Outermost ping ring — only on latest dot */}
                  {i === points.length - 1 && (
                    <circle cx={pt.x} cy={pt.y} r={animated ? 20 : 0}
                      fill="none" stroke={c} strokeWidth={0.8}
                      opacity={animated ? 0.2 : 0}
                      style={{
                        transition:`r ${0.6}s ease ${delay}, opacity 0.4s ease ${delay}`,
                        animation: animated ? "pulse 2.5s ease-in-out infinite" : "none",
                      }}
                    />
                  )}

                  {/* Large halo */}
                  <circle cx={pt.x} cy={pt.y}
                    r={animated ? (isH ? 16 : 12) : 0}
                    fill={`${c}10`}
                    stroke={`${c}30`}
                    strokeWidth={1}
                    style={{
                      transition:`r 0.55s cubic-bezier(.34,1.56,.64,1) ${delay}`,
                    }}
                  />

                  {/* Mid ring */}
                  <circle cx={pt.x} cy={pt.y}
                    r={animated ? (isH ? 10 : 7) : 0}
                    fill={`${c}20`}
                    stroke={`${c}50`}
                    strokeWidth={1.2}
                    style={{
                      transition:`r 0.5s cubic-bezier(.34,1.56,.64,1) ${delay}`,
                    }}
                  />

                  {/* Core dot */}
                  <circle cx={pt.x} cy={pt.y}
                    r={animated ? (isH ? 7 : 5) : 0}
                    fill={c}
                    filter="url(#dotGlow)"
                    style={{
                      transition:`r 0.45s cubic-bezier(.34,1.56,.64,1) ${delay}`,
                    }}
                  />

                  {/* Score label — large, always visible */}
                  <text
                    x={pt.x} y={pt.y - 20}
                    textAnchor="middle"
                    fill={c}
                    fontSize={15}
                    fontWeight="800"
                    fontFamily="monospace"
                    letterSpacing="-0.5"
                    style={{
                      opacity: animated ? 1 : 0,
                      transition:`opacity 0.45s ease ${parseFloat(delay)+0.15}s`,
                      filter:`drop-shadow(0 0 6px ${c}88)`,
                    }}
                  >
                    {pt.score}
                  </text>

                  {/* Grade badge under score */}
                  <text
                    x={pt.x} y={pt.y - 6}
                    textAnchor="middle"
                    fill={`${c}99`}
                    fontSize={9}
                    fontWeight="700"
                    fontFamily="monospace"
                    style={{
                      opacity: animated ? 0.7 : 0,
                      transition:`opacity 0.4s ease ${parseFloat(delay)+0.2}s`,
                    }}
                  >
                    {scoreGrade(pt.score)}
                  </text>

                  {/* PR label below chart — large */}
                  <text
                    x={pt.x} y={PADT + usableH + 20}
                    textAnchor="middle"
                    fill={isH ? T.textSub : T.textFaint}
                    fontSize={12}
                    fontWeight={isH ? "700" : "500"}
                    fontFamily="monospace"
                    style={{transition:"fill 0.15s, font-weight 0.15s"}}
                  >
                    {pt.name}
                  </text>

                  {/* Hover tooltip card */}
                  {isH && (
                    <g>
                      <rect
                        x={pt.x - 52} y={pt.y - 72}
                        width={104} height={46}
                        rx={8}
                        fill={T.tooltipRect}
                        stroke={c}
                        strokeWidth={1.2}
                        opacity={0.97}
                      />
                      <text x={pt.x} y={pt.y - 52}
                        textAnchor="middle" fill={c}
                        fontSize={18} fontWeight="900" fontFamily="monospace">
                        {pt.score}<tspan fontSize={10} fill={`${c}99`}>/100</tspan>
                      </text>
                      <text x={pt.x} y={pt.y - 34}
                        textAnchor="middle" fill={T.textMuted} fontSize={10} fontFamily="monospace">
                        {pt.name}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </div>
  );
}
/* ══════════════ SELECTED PR ANALYSIS — animated real-time ══════════════ */
function SelectedPRAnalysis({ pr }) {
  const T = useTheme();
  const [prevPR, setPrevPR] = useState(null);
  const [animKey, setAnimKey] = useState(0);

  useEffect(() => {
    if (pr?.id !== prevPR?.id) {
      setAnimKey(k => k + 1);
      setPrevPR(pr);
    }
  }, [pr?.id]);

  const rows = pr ? [
    {label:"Critical", val:pr.critical||0, color:"#ef4444", max:Math.max(pr.critical||1,1), glow:"rgba(239,68,68,0.35)"},
    {label:"High",     val:pr.highs||0,    color:"#f97316", max:Math.max(pr.highs||1,5),    glow:"rgba(249,115,22,0.35)"},
    {label:"Medium",   val:pr.mediums||0,  color:"#eab308", max:Math.max(pr.mediums||1,5),  glow:"rgba(234,179,8,0.3)"},
    {label:"Low",      val:pr.lows||0,     color:"#6b7280", max:Math.max(pr.lows||1,5),     glow:"rgba(107,114,128,0.25)"},
  ] : [];

  return (
    <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px",position:"relative",overflow:"hidden",transition:"background 0.3s"}}>
      {pr && (
        <div style={{
          position:"absolute",top:-40,right:-40,width:160,height:160,borderRadius:"50%",
          background:`radial-gradient(circle, ${pr.score>=85?"rgba(34,197,94,0.06)":pr.score>=65?"rgba(59,130,246,0.06)":"rgba(239,68,68,0.06)"} 0%, transparent 70%)`,
          pointerEvents:"none", animation:"pulseGlow 3s ease-in-out infinite",
        }}/>
      )}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <span style={{color:"#22c55e",fontSize:13}}>◎</span>
          <span style={{fontWeight:600,fontSize:15,color:T.textHeading}}>Selected PR Analysis</span>
        </div>
        {pr && (
          <div style={{display:"flex",alignItems:"center",gap:6,fontSize:11,color:"#22c55e",
            background:"rgba(34,197,94,0.08)",border:"1px solid rgba(34,197,94,0.2)",
            padding:"2px 8px",borderRadius:10,animation:"pulse 2s infinite"}}>
            <span style={{width:5,height:5,borderRadius:"50%",background:"#22c55e",display:"inline-block"}}/>
            Live
          </div>
        )}
      </div>
      {!pr ? (
        <div style={{textAlign:"center",padding:"40px 0",color:T.textMuted,fontSize:13}}>Click a PR above to analyse</div>
      ) : (
        <div key={animKey} style={{animation:"fadeIn 0.4s ease"}}>
          <div style={{display:"flex",gap:20,alignItems:"center",marginBottom:20}}>
            <ScoreRing score={pr.score} />
            <div>
              <div style={{fontSize:13,fontWeight:700,color:T.textHeading,marginBottom:4,fontFamily:"monospace"}}>{pr.name}</div>
              <div style={{fontSize:11,color:T.textFaint,marginBottom:6}}>{pr.author} · {pr.date}</div>
              <VerdictBadge v={pr.verdict}/>
            </div>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {rows.map(({label,val,color,max,glow},i) => {
              const pct = Math.min((val/max)*100, 100);
              return (
                <div key={label} style={{animation:`fadeIn 0.4s ease ${i*0.08}s both`}}>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
                    <span style={{fontSize:11,color:T.textMuted,letterSpacing:0.5}}>{label}</span>
                    <span style={{fontSize:13,fontWeight:800,color,fontFamily:"monospace"}}>{val}</span>
                  </div>
                  <div style={{height:6,background:T.bgInput,borderRadius:3,overflow:"hidden",position:"relative"}}>
                    <div style={{height:"100%",width:`${pct}%`,background:`linear-gradient(90deg, ${color}, ${color}cc)`,borderRadius:3,boxShadow:`0 0 8px ${glow}`,transition:"width 1.4s cubic-bezier(.34,1.56,.64,1)"}}/>
                    {val>0&&<div style={{position:"absolute",top:0,left:0,height:"100%",width:"30%",background:"linear-gradient(90deg,transparent,rgba(255,255,255,0.12),transparent)",animation:"shimmer 2s ease-in-out infinite",animationDelay:`${i*0.3}s`}}/>}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{display:"flex",gap:8,marginTop:16,paddingTop:14,borderTop:`1px solid ${T.borderFaint}`}}>
            {[
              {l:"Total", v:(pr.critical||0)+(pr.highs||0)+(pr.mediums||0)+(pr.lows||0), c:T.textSub},
              {l:"Score", v:`${pr.score}/100`, c:pr.score>=85?"#22c55e":pr.score>=65?"#3b82f6":"#ef4444"},
            ].map(({l,v,c})=>(
              <div key={l} style={{flex:1,background:T.bgSubtle,borderRadius:7,padding:"8px 10px",textAlign:"center"}}>
                <div style={{fontSize:16,fontWeight:800,color:c,fontFamily:"monospace"}}>{v}</div>
                <div style={{fontSize:10,color:T.textFaint,marginTop:2}}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════ LIVE AGENT ACTIVITY — polls every 5s ══════════════════ */
function LiveAgentActivity({ apiUrl, initialLog }) {
  const T = useTheme();
  const [log, setLog] = useState(initialLog || []);
  const [isLive, setIsLive] = useState(false);
  const [newIdx, setNewIdx] = useState(-1);
  const scrollRef = useRef(null);

  const fetchLog = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/dashboard`);
      if (!res.ok) return;
      const d = await res.json();
      const newLog = d.live_log || [];
      if (newLog.length > 0) {
        setLog(prev => {
          const topChanged = newLog[0]?.desc !== prev[0]?.desc;
          if (topChanged) { setNewIdx(0); setTimeout(() => setNewIdx(-1), 2000); }
          return newLog;
        });
        setIsLive(true);
      }
    } catch {}
  };

  useEffect(() => { fetchLog(); const id = setInterval(fetchLog, 5000); return () => clearInterval(id); }, []);
  useEffect(() => { if (log.length > 0) setIsLive(true); }, [initialLog]);
  useEffect(() => { scrollRef.current?.scrollTo({top:0, behavior:"smooth"}); }, [log]);

  const agentColorMap = {
    "Security Agent":"#ef4444","PR Review Agent":"#3b82f6","Docs Agent":"#22c55e",
    "Dependency Agent":"#f97316","Memory Agent":"#64748b","Auto-Fix Agent":"#06b6d4",
  };

  return (
    <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px",display:"flex",flexDirection:"column",transition:"background 0.3s"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <span style={{color:"#a855f7",fontSize:14}}>⚡</span>
          <span style={{fontWeight:600,fontSize:15,color:T.textHeading}}>Live Agent Activity</span>
        </div>
        <div style={{background:"rgba(168,85,247,0.1)",border:"1px solid rgba(168,85,247,0.25)",
          padding:"3px 10px",borderRadius:20,fontSize:11,color:"#c084fc",fontWeight:600,
          display:"flex",alignItems:"center",gap:5}}>
          <span style={{width:5,height:5,borderRadius:"50%",background:"#c084fc",display:"inline-block",animation:isLive?"pulse 1.5s infinite":"none"}}/>
          {isLive ? "Streaming" : "Waiting"}
        </div>
      </div>

      {log.length === 0 ? (
        <div style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:12,padding:"30px 0"}}>
          <div style={{display:"flex",gap:6}}>
            {[0,1,2,3,4].map(i=>(
              <div key={i} style={{width:6,height:6,borderRadius:"50%",background:T.bgInputAlt,
                animation:"pulse 1.5s ease-in-out infinite",animationDelay:`${i*0.15}s`}}/>
            ))}
          </div>
          <div style={{fontSize:12,color:T.textMuted}}>Waiting for agent activity...</div>
        </div>
      ) : (
        <div ref={scrollRef} style={{display:"flex",flexDirection:"column",gap:10,overflowY:"auto",maxHeight:280}}>
          {log.map((item, i) => {
            const dotColor = item.dot || agentColorMap[item.agent] || "#94a3b8";
            const isNew = i === newIdx;
            return (
              <div key={i} style={{
                display:"flex",alignItems:"flex-start",gap:12,
                padding:"10px 12px",borderRadius:8,
                background: isNew ? `${dotColor}12` : T.bgSubtle,
                border:`1px solid ${isNew ? `${dotColor}30` : T.borderFaint}`,
                animation:`logIn 0.35s ease ${i*0.07}s both`,
                transition:"background 0.4s, border-color 0.4s",
              }}>
                <div style={{position:"relative",marginTop:5,flexShrink:0}}>
                  <div style={{width:8,height:8,borderRadius:"50%",background:dotColor,
                    boxShadow:`0 0 ${isNew?"10px":"5px"} ${dotColor}`,
                    animation:i===0?"pulse 2s infinite":"none",transition:"box-shadow 0.3s"}}/>
                </div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:3}}>
                    <span style={{fontSize:12,fontWeight:700,color:dotColor,letterSpacing:0.2}}>{item.agent}</span>
                    <span style={{fontSize:10,color:T.textDim,flexShrink:0,marginLeft:8}}>{item.time}</span>
                  </div>
                  <div style={{fontSize:11,color:T.textMuted,lineHeight:1.5,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                    {item.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div style={{marginTop:12,paddingTop:10,borderTop:`1px solid ${T.borderFaint}`,
        display:"flex",alignItems:"center",justifyContent:"space-between",fontSize:10,color:T.textDim}}>
        <span>{log.length} events</span>
        <span>Refreshes every 5s</span>
      </div>
    </div>
  );
}

/* ══════════════ VOICE CHATBOT COMPONENT ══════════════════════════════════ */
function VoiceChatbot({ apiUrl }) {
  const T = useTheme();
  const [open, setOpen]         = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi! I'm RepoGuardian AI, connected to your memory store. Try asking:\n• What security issues does codewithVamshi5 have?\n• Which files have the most problems?\n• Is codewithVamshi5 improving?\n• Give me a full summary of codewithVamshi5" }
  ]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/dashboard`).then(r=>r.json()).catch(()=>{});
  }, [open]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    const newMessages = [...messages, { role: "user", text: q }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setMessages(m => [...m, { role: "assistant", text: data.reply || "No response." }]);
    } catch (e) {
      setMessages(m => [...m, { role: "assistant", text: `Could not reach backend. Error: ${e.message}` }]);
    }
    setLoading(false);
  };

  return (
    <>
      <button onClick={() => setOpen(o => !o)} style={{
        position:"fixed", bottom:24, right:24, zIndex:999,
        width:56, height:56, borderRadius:"50%",
        background:"linear-gradient(135deg,#3b82f6,#6366f1)",
        border:"none", cursor:"pointer", fontSize:24,
        boxShadow:"0 4px 20px rgba(59,130,246,0.5)",
        display:"flex", alignItems:"center", justifyContent:"center",
        transition:"transform 0.2s",
      }}>{open ? "✕" : "🤖"}</button>

      {open && (
        <div style={{
          position:"fixed", bottom:90, right:24, zIndex:998,
          width:360, height:500,
          background:T.bgCard, border:`1px solid ${T.border}`,
          borderRadius:16, display:"flex", flexDirection:"column",
          boxShadow:"0 8px 40px rgba(0,0,0,0.4)",
          animation:"fadeIn 0.2s ease", transition:"background 0.3s",
        }}>
          <div style={{padding:"14px 18px", borderBottom:`1px solid ${T.border}`, display:"flex", alignItems:"center", gap:10}}>
            <div style={{width:32,height:32,borderRadius:8,background:"linear-gradient(135deg,#3b82f6,#6366f1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16}}>🤖</div>
            <div>
              <div style={{fontWeight:700,fontSize:13,color:T.textHeading}}>RepoGuardian AI</div>
              <div style={{fontSize:10,color:"#22c55e"}}>● Connected to your dashboard</div>
            </div>
          </div>

          <div style={{flex:1,overflowY:"auto",padding:"14px 16px",display:"flex",flexDirection:"column",gap:10}}>
            {messages.map((m,i) => (
              <div key={i} style={{display:"flex", justifyContent:m.role==="user"?"flex-end":"flex-start"}}>
                <div style={{
                  maxWidth:"80%", padding:"9px 13px", borderRadius:12,
                  fontSize:13, lineHeight:1.5,
                  background: m.role==="user" ? "#3b82f6" : T.bgInputAlt,
                  color: m.role==="user" ? "#fff" : T.text,
                  borderBottomRightRadius:m.role==="user"?2:12,
                  borderBottomLeftRadius:m.role==="assistant"?2:12,
                }}>{m.text}</div>
              </div>
            ))}
            {loading && (
              <div style={{display:"flex",gap:4,padding:"8px 4px"}}>
                {[0,1,2].map(i=>(
                  <div key={i} style={{width:6,height:6,borderRadius:"50%",background:"#3b82f6",
                    animation:"pulse 1s infinite",animationDelay:`${i*0.2}s`}}/>
                ))}
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          <div style={{padding:"12px 16px",borderTop:`1px solid ${T.border}`,display:"flex",gap:8}}>
            <input
              value={input}
              onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&sendMessage()}
              placeholder="e.g. What security issues does codewithVamshi5 have?"
              style={{
                flex:1, background:T.bgInputAlt, border:`1px solid ${T.border}`,
                borderRadius:8, padding:"8px 12px", color:T.text, fontSize:13, outline:"none",
              }}
            />
            <button onClick={sendMessage} disabled={loading} style={{
              background:"#3b82f6", border:"none", borderRadius:8,
              padding:"8px 14px", color:"#fff", fontSize:13,
              cursor:loading?"not-allowed":"pointer", opacity:loading?0.6:1,
            }}>→</button>
          </div>
        </div>
      )}
    </>
  );
}

/* ══════════════════════ MAIN DASHBOARD ══════════════════════════════════ */
export default function Dashboard() {
  const [tab, setTab]         = useState("overview");
  const [filter, setFilter]   = useState("All");
  const [data, setData]       = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dark, setDark]       = useState(true);

  // ── PR limit gate ─────────────────────────────────────────────────────────
  const [prLimit,    setPrLimit]    = useState({ open: 0, limit: 5, exceeded: false, prs: [] });
  const [prBlocked,  setPrBlocked]  = useState(false);   // controls overlay visibility

  const fetchPrLimit = () => {
    fetch(`${API}/api/pr-limit`)
      .then(r => r.json())
      .then(d => {
        setPrLimit(d);
        // Auto-show overlay when limit is exceeded (only if not already dismissed)
        if (d.exceeded) setPrBlocked(true);
      })
      .catch(() => {});   // fail silently — don't break the dashboard
  };

  useEffect(() => {
    fetchPrLimit();
    const iv = setInterval(fetchPrLimit, 30000);   // poll every 30s
    return () => clearInterval(iv);
  }, []);

  const T = dark ? DARK : LIGHT;

  /* ── Fetch real data from FastAPI backend ── */
  const fetchData = () => {
    fetch(`${API}/api/dashboard`)
      .then(r => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      })
      .then(json => {
        setData(json);
        setLoading(false);
        setError(null);
        setLastUpdate(new Date().toLocaleTimeString());
      })
      .catch(err => {
        setError(`Cannot reach API at ${API} — is receiver.py running?`);
        setLoading(false);
      });
  };

  /* ── Fetch on mount + every 30 seconds ── */
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  /* ── Derived state from real data ── */
  const PULL_REQUESTS  = data.pull_requests  || [];
  const HEALTH_TREND   = data.health_trend   || [];
  const ISSUES_PER_PR  = data.issues_per_pr  || [];
  const FINDINGS       = data.findings       || [];
  const AGENTS_DATA    = data.agents_data    || [];
  const PIE_DATA       = data.pie_data       || [];
  const RADAR_DATA     = data.radar_data     || [];
  const LIVE_LOG       = data.live_log       || [];
  const stats          = data.stats          || EMPTY.stats;

  const [selPR, setSelPR] = useState(null);
  const activePR = selPR || PULL_REQUESTS[0] || null;

  // ── Git Report download state ─────────────────────────────────────────────
  const [gitReportLoading, setGitReportLoading] = useState(null); // stores pr.id while loading
  const [gitReportError,   setGitReportError]   = useState(null);

  const downloadGitReport = async (pr, e) => {
    e.stopPropagation(); // don't select the PR row
    setGitReportLoading(pr.id);
    setGitReportError(null);
    try {
      // pr.branch is "owner/repo" format from the API
      const [owner, repo] = (pr.branch || "").split("/");
      if (!owner || !repo) throw new Error(`Invalid repo format: "${pr.branch}"`);

      const res = await fetch(`${API}/api/git-report/${owner}/${repo}/${pr.id}`);
      if (!res.ok) {
        let detail = `Server error ${res.status}`;
        try { const j = await res.json(); detail = j.detail || j.error || detail; } catch(_) {}
        throw new Error(detail);
      }
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/pdf")) {
        let detail = "Response is not a PDF.";
        try { const j = await res.json(); detail = j.detail || j.error || detail; } catch(_) {}
        throw new Error(detail);
      }
      const blob = await res.blob();
      if (blob.size < 100) throw new Error("Generated PDF appears empty.");
      const url = URL.createObjectURL(blob);
      const a   = document.createElement("a");
      a.href     = url;
      a.download = `GitReport_${pr.branch?.replace("/","_")}_PR${pr.id}_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch(err) {
      setGitReportError(`PR #${pr.id}: ${err.message}`);
      setTimeout(() => setGitReportError(null), 6000);
    } finally {
      setGitReportLoading(null);
    }
  };

  const filteredFindings = filter === "All"
    ? FINDINGS
    : FINDINGS.filter(f => f.agent === AGENT_FILTER_MAP[filter]);

  const TABS = [
    {key:"overview", label:"Overview", icon:"◎"},
    {key:"findings", label:"Findings", icon:"⚑"},
    {key:"agents",   label:"Agents",   icon:"⚙"},
    {key:"history",  label:"History",  icon:"◷"},
  ];

  return (
    <ThemeContext.Provider value={T}>
    <div style={{minHeight:"100vh",background:T.bg,color:T.text,fontFamily:"'Inter','Segoe UI',sans-serif",transition:"background 0.3s, color 0.3s"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        ::-webkit-scrollbar{width:4px;}
        ::-webkit-scrollbar-thumb{background:${T.scrollThumb};border-radius:2px;}
        @keyframes fadeIn    {from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
        @keyframes pulse     {0%,100%{opacity:1}50%{opacity:0.35}}
        @keyframes logIn     {from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
        @keyframes pulseGlow {0%,100%{opacity:0.5;transform:scale(1)}50%{opacity:1;transform:scale(1.15)}}
        @keyframes shimmer   {0%{transform:translateX(-200%)}100%{transform:translateX(400%)}}
        @keyframes spin      {from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
        .tab-btn:hover{color:${T.textHeading}!important;}
        .pr-row:hover{background:${T.bgInput}!important;cursor:pointer;}
        .finding-card:hover{background:${T.bgSubtle}!important;}
        .agent-card:hover{border-color:rgba(59,130,246,0.35)!important;background:rgba(59,130,246,0.04)!important;}
        .filter-btn:hover{background:${T.bgInput}!important;}
        .history-row:hover{background:${T.bgSubtle}!important;}
      `}</style>

      {/* ── NAVBAR ── */}
      <nav style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 24px",height:62,background:T.nav,borderBottom:`1px solid ${T.navBorder}`,position:"sticky",top:0,zIndex:100,transition:"background 0.3s"}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:34,height:34,borderRadius:8,background:"linear-gradient(135deg,#3b82f6,#6366f1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:17}}>🛡</div>
          <div>
            <div style={{fontWeight:700,fontSize:15,color:T.textHeading,letterSpacing:-0.2}}>RepoGuardian</div>
            <div style={{fontSize:10,color:T.textFaint,letterSpacing:0.8}}>AI-Powered Code Review System</div>
          </div>
        </div>

        <div style={{display:"flex",gap:2}}>
          {TABS.map(({key,label,icon}) => (
            <button key={key} className="tab-btn" onClick={() => setTab(key)} style={{
              display:"flex",alignItems:"center",gap:6,
              padding:"7px 18px",borderRadius:6,border:"none",cursor:"pointer",
              fontSize:13,fontWeight:500,transition:"all 0.15s",
              background:"transparent",
              color: tab===key ? T.textHeading : T.textMuted,
              borderBottom:`2px solid ${tab===key ? "#3b82f6" : "transparent"}`,
            }}>
              <span style={{fontSize:13}}>{icon}</span>{label}
            </button>
          ))}
        </div>

        <div style={{display:"flex",alignItems:"center",gap:10}}>
          {error ? (
            <div style={{display:"flex",alignItems:"center",gap:6,background:T.errBg,border:`1px solid ${T.errBorder}`,padding:"4px 12px",borderRadius:20}}>
              <span style={{width:7,height:7,borderRadius:"50%",background:"#ef4444",display:"inline-block"}}/>
              <span style={{fontSize:12,color:"#ef4444",fontWeight:600}}>Offline</span>
            </div>
          ) : (
            <div style={{display:"flex",alignItems:"center",gap:6,background:"rgba(34,197,94,0.08)",border:"1px solid rgba(34,197,94,0.2)",padding:"4px 12px",borderRadius:20}}>
              <span style={{width:7,height:7,borderRadius:"50%",background:"#22c55e",display:"inline-block",animation:"pulse 2s infinite"}}/>
              <span style={{fontSize:12,color:"#22c55e",fontWeight:600}}>Live {lastUpdate && `· ${lastUpdate}`}</span>
            </div>
          )}
          {/* ☀️/🌙 Theme toggle */}
          <ThemeToggle dark={dark} onToggle={() => setDark(d => !d)} />

          {/* PR limit indicator — clickable to re-show overlay if exceeded */}
          <div
            onClick={() => { if (prLimit.exceeded) setPrBlocked(true); }}
            style={{
              display:"flex", alignItems:"center", gap:6,
              background: prLimit.exceeded
                ? "rgba(248,81,73,0.1)"
                : prLimit.open >= prLimit.limit - 1
                ? "rgba(251,133,0,0.1)"
                : "rgba(63,185,80,0.08)",
              border: `1px solid ${prLimit.exceeded ? "rgba(248,81,73,0.35)" : prLimit.open >= prLimit.limit - 1 ? "rgba(251,133,0,0.3)" : "rgba(63,185,80,0.2)"}`,
              padding:"4px 12px", borderRadius:20,
              cursor: prLimit.exceeded ? "pointer" : "default",
            }}
            title={prLimit.exceeded ? "Click to view blocked PRs" : `${prLimit.limit - prLimit.open} PR slots remaining`}
          >
            <span style={{
              width:7, height:7, borderRadius:"50%", display:"inline-block",
              background: prLimit.exceeded ? "#f85149" : prLimit.open >= prLimit.limit - 1 ? "#fb8500" : "#3fb950",
              animation: prLimit.exceeded ? "pulse 1.5s infinite" : "none",
            }}/>
            <span style={{
              fontSize:12, fontWeight:600,
              color: prLimit.exceeded ? "#f85149" : prLimit.open >= prLimit.limit - 1 ? "#fb8500" : "#3fb950",
              fontFamily:"monospace",
            }}>
              {prLimit.open}/{prLimit.limit} PRs
            </span>
          </div>

          <div style={{background:"rgba(99,102,241,0.12)",border:"1px solid rgba(99,102,241,0.25)",padding:"4px 12px",borderRadius:20,fontSize:12,color:"#818cf8",fontWeight:500}}>
            llama3-70b via Groq
          </div>
        </div>
      </nav>

      {/* ── ERROR BANNER ── */}
      {error && (
        <div style={{background:T.errBg,border:`1px solid ${T.errBorder}`,borderRadius:8,margin:"16px 24px",padding:"12px 16px",fontSize:13,color:"#fca5a5"}}>
          ⚠ {error} — Run: <code style={{fontFamily:"monospace",background:"rgba(0,0,0,0.3)",padding:"2px 6px",borderRadius:4}}>uvicorn webhook.receiver:app --port 8000</code>
        </div>
      )}

      {/* ── LOADING ── */}
      {loading && !error && (
        <div style={{textAlign:"center",padding:"80px 0",color:T.textMuted,fontSize:14}}>
          Loading real data from RepoGuardian API...
        </div>
      )}

      {!loading && (
      <div style={{padding:"24px",maxWidth:1400,margin:"0 auto"}}>

        {/* ════════ OVERVIEW ════════ */}
        {tab === "overview" && (
          <div style={{animation:"fadeIn 0.3s ease"}}>
            <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:24}}>
              <StatCard icon="◎" label="Avg Health Score"  value={stats.avg_score}      color="#22c55e" />
              <StatCard icon="⇄" label="PRs Reviewed"      value={stats.total_prs}       color={T.text} />
              <StatCard icon="⚠" label="Critical Issues"   value={stats.critical_count}  color="#ef4444" />
              <StatCard icon="⚙" label="Total Findings"    value={stats.total_findings}  color={T.text} />
            </div>

            <div style={{display:"grid",gridTemplateColumns:"1fr 420px",gap:16,marginBottom:16}}>
              <WavyHealthTrend data={HEALTH_TREND} />
              <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 20px",display:"flex",flexDirection:"column",transition:"background 0.3s"}}>
                <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    <span style={{color:"#3b82f6"}}>⇄</span>
                    <span style={{fontWeight:600,fontSize:15,color:T.textHeading}}>Recent Pull Requests</span>
                  </div>
                  {PULL_REQUESTS.length>0&&<span style={{fontSize:11,color:T.textFaint,background:T.bgInput,padding:"2px 8px",borderRadius:10}}>{PULL_REQUESTS.length} total</span>}
                </div>

                {/* Git Report error toast */}
                {gitReportError && (
                  <div style={{
                    background:"rgba(239,68,68,0.08)",border:"1px solid rgba(239,68,68,0.2)",
                    borderRadius:7,padding:"8px 12px",marginBottom:10,
                    fontSize:11,color:"#fca5a5",lineHeight:1.5,
                  }}>⚠ {gitReportError}</div>
                )}

                {PULL_REQUESTS.length === 0 ? (
                  <div style={{textAlign:"center",padding:"40px 0",color:T.textMuted,fontSize:13}}>No PRs reviewed yet</div>
                ) : (
                <div style={{display:"flex",flexDirection:"column",gap:6,overflowY:"auto",maxHeight:310}}>
                  {PULL_REQUESTS.map((pr,i) => (
                    <div key={pr.id} className="pr-row" onClick={() => setSelPR(pr)} style={{
                      padding:"11px 13px",borderRadius:9,
                      background: activePR?.id===pr.id ? "rgba(59,130,246,0.09)" : T.bgSubtle,
                      border:`1px solid ${activePR?.id===pr.id ? "rgba(59,130,246,0.28)" : T.borderFaint}`,
                      transition:"all 0.18s",cursor:"pointer",
                      animation:`fadeIn 0.3s ease ${i*0.06}s both`,
                    }}>
                      {/* Row top: PR name + verdict */}
                      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:5}}>
                        <span style={{fontSize:12,fontWeight:700,color:T.textHeading,fontFamily:"monospace",letterSpacing:-0.3}}>{pr.name}</span>
                        <VerdictBadge v={pr.verdict} />
                      </div>

                      {/* Row bottom: author + score bar + Git Report button */}
                      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8}}>
                        <span style={{fontSize:11,color:T.textFaint,flexShrink:0}}>{pr.author}</span>

                        <div style={{display:"flex",alignItems:"center",gap:8,marginLeft:"auto"}}>
                          {/* Score bar */}
                          <div style={{display:"flex",alignItems:"center",gap:6}}>
                            <div style={{height:3,width:36,background:T.bgInput,borderRadius:2,overflow:"hidden"}}>
                              <div style={{height:"100%",width:`${pr.score}%`,background:pr.score>=85?"#22c55e":pr.score>=65?"#3b82f6":"#ef4444",borderRadius:2}}/>
                            </div>
                            <span style={{fontSize:12,color:pr.score>=85?"#22c55e":pr.score>=65?"#3b82f6":"#f97316",fontWeight:800,fontFamily:"monospace"}}>{pr.score}</span>
                          </div>

                          {/* Git Report button */}
                          <button
                            onClick={(e) => downloadGitReport(pr, e)}
                            disabled={gitReportLoading === pr.id}
                            title="Download Git PR Report PDF"
                            style={{
                              display:"flex",alignItems:"center",gap:5,
                              padding:"3px 9px",borderRadius:6,
                              background: gitReportLoading===pr.id ? "rgba(139,92,246,0.08)" : "rgba(139,92,246,0.12)",
                              border:`1px solid ${gitReportLoading===pr.id ? "rgba(139,92,246,0.15)" : "rgba(139,92,246,0.3)"}`,
                              color: gitReportLoading===pr.id ? T.textMuted : "#a78bfa",
                              fontSize:10,fontWeight:700,cursor: gitReportLoading===pr.id ? "not-allowed" : "pointer",
                              letterSpacing:0.3,transition:"all 0.15s",whiteSpace:"nowrap",
                            }}
                            onMouseEnter={e=>{ if(gitReportLoading!==pr.id) e.currentTarget.style.background="rgba(139,92,246,0.22)"; }}
                            onMouseLeave={e=>{ e.currentTarget.style.background= gitReportLoading===pr.id?"rgba(139,92,246,0.08)":"rgba(139,92,246,0.12)"; }}
                          >
                            {gitReportLoading===pr.id ? (
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                                style={{animation:"spin 1s linear infinite"}}>
                                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                              </svg>
                            ) : (
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                <polyline points="14 2 14 8 20 8"/>
                                <line x1="12" y1="18" x2="12" y2="12"/>
                                <line x1="9" y1="15" x2="15" y2="15"/>
                              </svg>
                            )}
                            {gitReportLoading===pr.id ? "Generating…" : "Git Report"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                )}
              </div>
            </div>

            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
              <SelectedPRAnalysis pr={activePR} />
              <LiveAgentActivity apiUrl={API} initialLog={LIVE_LOG} />
            </div>
          </div>
        )}

        {/* ════════ FINDINGS ════════ */}
        {tab === "findings" && (
          <div style={{animation:"fadeIn 0.3s ease"}}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:24}}>
              <div style={{display:"flex",alignItems:"center",gap:12}}>
                <span style={{fontSize:13,color:T.textMuted,display:"flex",alignItems:"center",gap:6}}>⚑ Filter by Agent:</span>
                <div style={{display:"flex",gap:6}}>
                  {["All","Security","Dependency","Review","Complexity"].map(f => (
                    <button key={f} className="filter-btn" onClick={() => setFilter(f)} style={{
                      padding:"5px 14px",borderRadius:6,border:"none",cursor:"pointer",
                      fontSize:12,fontWeight:500,transition:"all 0.15s",
                      background: filter===f ? "#3b82f6" : T.bgInputAlt,
                      color: filter===f ? "#fff" : T.textSub,
                    }}>{f}</button>
                  ))}
                </div>
              </div>
              <span style={{fontSize:13,color:T.textMuted}}>{filteredFindings.length} findings</span>
            </div>
            {filteredFindings.length === 0 ? (
              <div style={{textAlign:"center",padding:"80px 0",color:T.textMuted,fontSize:14}}>No findings yet — run the orchestrator on a PR first</div>
            ) : (
            <div style={{display:"flex",flexDirection:"column",gap:12}}>
              {filteredFindings.map((f,i) => {
                const sevColor = SEV_CFG[f.severity]?.color || "#6b7280";
                return (
                  <div key={f.id} className="finding-card" style={{
                    background:T.bgCard, border:`1px solid ${T.border}`,
                    borderLeft:`3px solid ${sevColor}`,
                    borderRadius:10, padding:"18px 20px",
                    transition:"all 0.15s", animation:`fadeIn 0.3s ease ${i*0.05}s both`,
                  }}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                      <div style={{display:"flex",alignItems:"center",gap:8}}>
                        <SevBadge sev={f.severity} />
                        <AgentBadge name={f.agent} />
                      </div>
                      <div style={{display:"flex",alignItems:"center",gap:6,fontSize:12,color:T.textMuted}}>
                        <span>📄</span>
                        <span style={{fontFamily:"monospace",color:T.textSub}}>{f.file}:{f.line}</span>
                      </div>
                    </div>
                    <div style={{fontSize:14,fontWeight:500,color:T.textHeading,marginBottom:12}}>{f.message}</div>
                    <div style={{background:T.fixBg,border:`1px solid ${T.fixBorder}`,borderRadius:7,padding:"10px 14px"}}>
                      <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}>
                        <span style={{color:"#22c55e",fontSize:13}}>◉</span>
                        <span style={{fontSize:12,fontWeight:600,color:"#22c55e"}}>Suggested Fix:</span>
                      </div>
                      <div style={{fontSize:13,color:T.textSub,fontFamily:"monospace"}}>{f.fix}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            )}
          </div>
        )}

        {/* ════════ AGENTS ════════ */}
        {tab === "agents" && (
          <div style={{animation:"fadeIn 0.3s ease"}}>
            {data.last_run && data.last_run.pr_number && (
              <div style={{background:"rgba(59,130,246,0.06)",border:"1px solid rgba(59,130,246,0.2)",borderRadius:8,padding:"10px 16px",marginBottom:20,display:"flex",flexWrap:"wrap",gap:24,alignItems:"center",fontSize:12}}>
                <span style={{color:T.textMuted}}>Last run:</span>
                <span style={{color:T.textHeading,fontFamily:"monospace",fontWeight:600}}>PR #{data.last_run.pr_number}</span>
                <span style={{color:T.textMuted}}>Score:</span>
                <span style={{color:data.last_run.score>=85?"#22c55e":data.last_run.score>=65?"#3b82f6":"#ef4444",fontWeight:700,fontFamily:"monospace"}}>{data.last_run.score}/100</span>
                <span style={{color:T.textMuted}}>Time:</span>
                <span style={{color:T.textSub,fontFamily:"monospace"}}>{data.last_run.elapsed}s</span>
              </div>
            )}

            <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16,marginBottom:24}}>
              {AGENTS_DATA.map((agent,i) => {
                const maxF = Math.max(...AGENTS_DATA.map(a=>a.findings),1);
                const pct  = Math.round((agent.findings/maxF)*100);
                const bc   = agent.color || "#3b82f6";
                return (
                <div key={agent.name} className="agent-card" style={{
                  background:T.bgCard,
                  border:`1px solid ${agent.status==="active"?`${bc}35`:T.border}`,
                  borderRadius:12, padding:"20px 22px", transition:"all 0.2s",
                  animation:`fadeIn 0.35s ease ${i*0.05}s both`,
                }}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:14}}>
                    <div style={{width:40,height:40,borderRadius:10,background:`${bc}18`,border:`1px solid ${bc}40`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>⚙</div>
                    <span style={{
                      fontSize:11,fontWeight:600,padding:"3px 10px",borderRadius:20,
                      background:agent.status==="active"?"rgba(34,197,94,0.1)":agent.status==="ran"?"rgba(59,130,246,0.1)":"rgba(107,114,128,0.1)",
                      color:agent.status==="active"?"#22c55e":agent.status==="ran"?"#60a5fa":"#9ca3af",
                      border:`1px solid ${agent.status==="active"?"rgba(34,197,94,0.25)":agent.status==="ran"?"rgba(59,130,246,0.25)":"rgba(107,114,128,0.2)"}`,
                    }}>{agent.status}</span>
                  </div>
                  <div style={{fontSize:15,fontWeight:700,color:T.textHeading,marginBottom:2}}>{agent.name}</div>
                  <div style={{fontSize:11,color:T.textMuted,marginBottom:14,fontFamily:"monospace"}}>{agent.model}</div>

                  {agent.name==="Auto-Fix Agent" ? (
                    <div style={{background:"rgba(6,182,212,0.07)",border:"1px solid rgba(6,182,212,0.2)",borderRadius:8,padding:"10px 12px",marginBottom:14}}>
                      <div style={{fontSize:20,fontWeight:800,fontFamily:"monospace",color:agent.fixes_applied>0?"#06b6d4":T.textDim,marginBottom:2}}>{agent.fixes_applied||0}</div>
                      <div style={{fontSize:11,color:T.textMuted}}>fixes applied automatically</div>
                      {agent.fix_pr_url && <a href={agent.fix_pr_url} target="_blank" rel="noreferrer" style={{fontSize:11,color:"#06b6d4",textDecoration:"none",display:"block",marginTop:4}}>View Fix PR →</a>}
                    </div>
                  ) : agent.name==="Memory Agent" ? (
                    <div style={{background:"rgba(100,116,139,0.07)",border:"1px solid rgba(100,116,139,0.2)",borderRadius:8,padding:"10px 12px",marginBottom:14}}>
                      <div style={{fontSize:20,fontWeight:800,fontFamily:"monospace",color:agent.recurring_alerts>0?"#94a3b8":T.textDim,marginBottom:2}}>{agent.recurring_alerts||0}</div>
                      <div style={{fontSize:11,color:T.textMuted}}>recurring alerts{agent.developer?` for @${agent.developer}`:""}</div>
                    </div>
                  ) : agent.name==="Dependency Agent" ? (
                    <div style={{marginBottom:14}}>
                      <div style={{display:"flex",gap:8,marginBottom:8}}>
                        {[["CVE",agent.highs||0,"#ef4444"],["ADV",agent.mediums||0,"#eab308"],["OK",agent.lows||0,"#22c55e"]].map(([l,v,c])=>(
                          <div key={l} style={{flex:1,background:T.bgInput,borderRadius:6,padding:"6px 8px",textAlign:"center"}}>
                            <div style={{fontSize:16,fontWeight:800,fontFamily:"monospace",color:v>0?c:T.textDim}}>{v}</div>
                            <div style={{fontSize:10,color:T.textFaint}}>{l}</div>
                          </div>
                        ))}
                      </div>
                      {agent.findings===0 && <div style={{fontSize:11,color:T.textFaint,textAlign:"center"}}>No vulnerable deps found</div>}
                    </div>
                  ) : agent.name!=="Orchestrator" ? (
                    <div style={{display:"flex",gap:8,marginBottom:14}}>
                      {[["H",agent.highs||0,"#ef4444"],["M",agent.mediums||0,"#eab308"],["L",agent.lows||0,"#6b7280"]].map(([l,v,c])=>(
                        <div key={l} style={{flex:1,background:T.bgInput,borderRadius:6,padding:"6px 8px",textAlign:"center"}}>
                          <div style={{fontSize:16,fontWeight:800,fontFamily:"monospace",color:v>0?c:T.textDim}}>{v}</div>
                          <div style={{fontSize:10,color:T.textFaint}}>{l}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
                    <span style={{fontSize:12,color:T.textMuted}}>
                      {agent.name==="Auto-Fix Agent"?"fixes":agent.name==="Memory Agent"?"alerts tracked":"total findings"}
                    </span>
                    <span style={{fontSize:20,fontWeight:800,fontFamily:"monospace",color:agent.findings>0?bc:T.textDim}}>
                      {agent.name==="Auto-Fix Agent"?(agent.fixes_applied||0):agent.name==="Memory Agent"?(agent.recurring_alerts||0):agent.findings}
                    </span>
                  </div>
                  <div style={{height:4,background:T.bgInput,borderRadius:2,overflow:"hidden"}}>
                    <div style={{height:"100%",width:`${pct}%`,background:bc,borderRadius:2,transition:"width 1.2s ease"}}/>
                  </div>
                </div>
                );
              })}
            </div>

            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
              <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:16}}>
                  <span style={{color:"#3b82f6"}}>◉</span>
                  <span style={{fontWeight:600,fontSize:15,color:T.textHeading}}>Codebase Health Radar</span>
                </div>
                {RADAR_DATA.length===0 ? (
                  <div style={{textAlign:"center",padding:"60px 0",color:T.textMuted,fontSize:13}}>No data yet</div>
                ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={RADAR_DATA} margin={{top:10,right:30,bottom:10,left:30}}>
                    <PolarGrid stroke={T.polarGrid} />
                    <PolarAngleAxis dataKey="subject" tick={{fill:T.textSub,fontSize:12}} />
                    <Radar dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={2} dot={{fill:"#3b82f6",r:4}} />
                  </RadarChart>
                </ResponsiveContainer>
                )}
              </div>

              <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
                <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:16}}>
                  <span style={{color:"#a855f7"}}>⚡</span>
                  <span style={{fontWeight:600,fontSize:15,color:T.textHeading}}>Findings by Agent</span>
                </div>
                {PIE_DATA.length===0 ? (
                  <div style={{textAlign:"center",padding:"60px 0",color:T.textMuted,fontSize:13}}>No data yet</div>
                ) : (<>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={PIE_DATA} cx="50%" cy="50%" outerRadius={82} innerRadius={46} dataKey="value" paddingAngle={3}>
                        {PIE_DATA.map((e,i) => <Cell key={i} fill={e.color} stroke="transparent" />)}
                      </Pie>
                      <Tooltip content={<DarkTip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{display:"flex",flexWrap:"wrap",gap:12,justifyContent:"center",marginTop:10}}>
                    {PIE_DATA.map(({name,color,value}) => (
                      <div key={name} style={{display:"flex",alignItems:"center",gap:6,fontSize:12}}>
                        <span style={{width:8,height:8,borderRadius:2,background:color,display:"inline-block"}}/>
                        <span style={{color:T.textMuted}}>{name}</span>
                        <span style={{color,fontWeight:700,fontFamily:"monospace"}}>{value}</span>
                      </div>
                    ))}
                  </div>
                </>)}
              </div>
            </div>
          </div>
        )}

        {/* ════════ HISTORY ════════ */}
        {tab === "history" && (
          <div style={{animation:"fadeIn 0.3s ease"}}>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:24}}>
              <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
                <div style={{fontWeight:600,fontSize:15,marginBottom:20,color:T.textHeading}}>Health Score Over Time</div>
                {HEALTH_TREND.length === 0 ? (
                  <div style={{textAlign:"center",padding:"60px 0",color:T.textMuted,fontSize:13}}>No history yet</div>
                ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={HEALTH_TREND}>
                    <CartesianGrid strokeDasharray="3 3" stroke={T.gridStroke} />
                    <XAxis dataKey="name" tick={{fontSize:11,fill:T.textMuted,fontFamily:"monospace"}} axisLine={false} tickLine={false} />
                    <YAxis domain={[0,100]} tick={{fontSize:11,fill:T.textMuted}} axisLine={false} tickLine={false} />
                    <Tooltip content={<DarkTip />} />
                    <Line type="monotone" dataKey="score" name="Score" stroke="#22c55e" strokeWidth={2.5}
                      dot={{fill:"#22c55e",r:5,strokeWidth:2,stroke:T.bg}} activeDot={{r:7}} />
                  </LineChart>
                </ResponsiveContainer>
                )}
              </div>

              <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
                <div style={{fontWeight:600,fontSize:15,marginBottom:20,color:T.textHeading}}>Issues per PR</div>
                {ISSUES_PER_PR.length === 0 ? (
                  <div style={{textAlign:"center",padding:"60px 0",color:T.textMuted,fontSize:13}}>No history yet</div>
                ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={ISSUES_PER_PR} barSize={30}>
                    <CartesianGrid strokeDasharray="3 3" stroke={T.gridStroke} />
                    <XAxis dataKey="name" tick={{fontSize:11,fill:T.textMuted,fontFamily:"monospace"}} axisLine={false} tickLine={false} />
                    <YAxis tick={{fontSize:11,fill:T.textMuted}} axisLine={false} tickLine={false} />
                    <Tooltip content={<DarkTip />} />
                    <Bar dataKey="critical" name="critical" stackId="a" fill="#ef4444" />
                    <Bar dataKey="high"     name="high"     stackId="a" fill="#f97316" />
                    <Bar dataKey="low"      name="low"      stackId="a" fill="#22c55e" />
                    <Bar dataKey="medium"   name="medium"   stackId="a" fill="#3b82f6" radius={[3,3,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
                )}
                <div style={{display:"flex",gap:16,justifyContent:"center",marginTop:12}}>
                  {[["critical","#ef4444"],["high","#f97316"],["low","#22c55e"],["medium","#3b82f6"]].map(([l,c]) => (
                    <div key={l} style={{display:"flex",alignItems:"center",gap:5,fontSize:11}}>
                      <span style={{width:10,height:10,borderRadius:2,background:c,display:"inline-block"}}/>
                      <span style={{color:T.textMuted}}>{l}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,overflow:"hidden"}}>
              <table style={{width:"100%",borderCollapse:"collapse"}}>
                <thead>
                  <tr style={{borderBottom:`1px solid ${T.border}`}}>
                    {["PR Name","Branch","Author","Score","Verdict","Timestamp"].map(h => (
                      <th key={h} style={{padding:"14px 18px",textAlign:"left",fontSize:12,fontWeight:600,color:T.textMuted,letterSpacing:0.3}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PULL_REQUESTS.length === 0 ? (
                    <tr><td colSpan={6} style={{padding:"40px",textAlign:"center",color:T.textMuted,fontSize:13}}>No PRs reviewed yet</td></tr>
                  ) : PULL_REQUESTS.map((pr) => (
                    <tr key={pr.id} className="history-row" style={{borderBottom:`1px solid ${T.borderFaint}`,transition:"background 0.15s"}}>
                      <td style={{padding:"14px 18px",fontSize:13,color:T.textHeading,fontFamily:"monospace",fontWeight:500}}>{pr.name}</td>
                      <td style={{padding:"14px 18px",fontSize:12,color:T.textMuted,fontFamily:"monospace"}}>{pr.branch}</td>
                      <td style={{padding:"14px 18px",fontSize:12,color:T.textSub}}>{pr.author}</td>
                      <td style={{padding:"14px 18px"}}>
                        <span style={{fontSize:15,fontWeight:800,fontFamily:"monospace",color:pr.score>=85?"#22c55e":pr.score>=65?"#3b82f6":"#f97316"}}>{pr.score}</span>
                      </td>
                      <td style={{padding:"14px 18px"}}><VerdictBadge v={pr.verdict} /></td>
                      <td style={{padding:"14px 18px",fontSize:12,color:T.textMuted,fontFamily:"monospace"}}>{pr.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
      )}

      {/* ══════════════ PR LIMIT BLOCKER ══════════════ */}
      <PRScreenBlock
        open={prLimit.open}
        limit={prLimit.limit}
        prs={prLimit.prs}
        visible={prBlocked}
        onDismiss={() => setPrBlocked(false)}
      />

      {/* ══════════════ VOICE CHATBOT ══════════════ */}
      <VoiceChatbot apiUrl={API} />
    </div>
    </ThemeContext.Provider>
  );
}