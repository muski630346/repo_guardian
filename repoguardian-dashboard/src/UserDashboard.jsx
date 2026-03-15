import { useState, useEffect, useContext, createContext } from "react";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";

const API = "http://localhost:8000";

/* ─── Theme tokens ───────────────────────────────────────────────────────── */
const ThemeContext = createContext();
const useTheme = () => useContext(ThemeContext);

const DARK = {
  bg:          "#0d1117",
  bgCard:      "#161b22",
  bgSubtle:    "rgba(255,255,255,0.03)",
  bgInput:     "rgba(255,255,255,0.04)",
  border:      "rgba(255,255,255,0.08)",
  borderHover: "rgba(59,130,246,0.35)",
  nav:         "#0d1117",
  navBorder:   "rgba(255,255,255,0.08)",
  text:        "#e2e8f0",
  textHeading: "#f1f5f9",
  textMuted:   "#64748b",
  textSub:     "#94a3b8",
  gridStroke:  "rgba(255,255,255,0.04)",
  polarGrid:   "rgba(255,255,255,0.07)",
  scrollThumb: "rgba(255,255,255,0.1)",
  tipBg:       "#1a2035",
  tipBorder:   "rgba(255,255,255,0.1)",
  fixBg:       "rgba(34,197,94,0.06)",
  fixBorder:   "rgba(34,197,94,0.14)",
  recBg:       "rgba(239,68,68,0.05)",
  recBorder:   "rgba(239,68,68,0.15)",
  tabBorder:   "rgba(255,255,255,0.08)",
  errBg:       "rgba(239,68,68,0.08)",
  errBorder:   "rgba(239,68,68,0.2)",
  isDark:      true,
};

const LIGHT = {
  bg:          "#f1f5f9",
  bgCard:      "#ffffff",
  bgSubtle:    "rgba(0,0,0,0.02)",
  bgInput:     "rgba(0,0,0,0.04)",
  border:      "rgba(0,0,0,0.08)",
  borderHover: "rgba(59,130,246,0.5)",
  nav:         "#ffffff",
  navBorder:   "rgba(0,0,0,0.08)",
  text:        "#1e293b",
  textHeading: "#0f172a",
  textMuted:   "#64748b",
  textSub:     "#475569",
  gridStroke:  "rgba(0,0,0,0.05)",
  polarGrid:   "rgba(0,0,0,0.1)",
  scrollThumb: "rgba(0,0,0,0.15)",
  tipBg:       "#ffffff",
  tipBorder:   "rgba(0,0,0,0.12)",
  fixBg:       "rgba(34,197,94,0.07)",
  fixBorder:   "rgba(34,197,94,0.2)",
  recBg:       "rgba(239,68,68,0.04)",
  recBorder:   "rgba(239,68,68,0.18)",
  tabBorder:   "rgba(0,0,0,0.08)",
  errBg:       "rgba(239,68,68,0.06)",
  errBorder:   "rgba(239,68,68,0.2)",
  isDark:      false,
};

/* ─── Theme Toggle ───────────────────────────────────────────────────────── */
function ThemeToggle({ dark, onToggle }) {
  const T = dark ? DARK : LIGHT;
  return (
    <button onClick={onToggle}
      title={dark ? "Switch to day mode" : "Switch to night mode"}
      style={{
        display:"flex", alignItems:"center", gap:8,
        background: dark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
        border: `1px solid ${T.border}`,
        borderRadius:20, padding:"5px 12px", cursor:"pointer",
        transition:"all 0.25s", color:T.textSub, fontSize:12, fontWeight:600,
      }}
    >
      <div style={{
        width:36, height:20, borderRadius:10, position:"relative",
        background: dark ? "#3b82f6" : "#cbd5e1", transition:"background 0.3s", flexShrink:0,
      }}>
        <div style={{
          position:"absolute", top:3,
          left: dark ? 19 : 3,
          width:14, height:14, borderRadius:"50%", background:"#fff",
          boxShadow:"0 1px 3px rgba(0,0,0,0.3)", transition:"left 0.3s",
        }}/>
      </div>
      <span>{dark ? "🌙 Night" : "☀️ Day"}</span>
    </button>
  );
}

/* ─── Severity config ────────────────────────────────────────────────────── */
const SEV_CFG = {
  HIGH:   { color:"#ef4444", bg:"rgba(239,68,68,0.12)",   border:"rgba(239,68,68,0.3)"   },
  MEDIUM: { color:"#eab308", bg:"rgba(234,179,8,0.12)",   border:"rgba(234,179,8,0.3)"   },
  LOW:    { color:"#6b7280", bg:"rgba(107,114,128,0.1)",  border:"rgba(107,114,128,0.25)"},
};

const TREND_CFG = {
  improving: { color:"#22c55e", icon:"↗", label:"Improving" },
  declining:  { color:"#ef4444", icon:"↘", label:"Declining"  },
  stable:     { color:"#3b82f6", icon:"→", label:"Stable"     },
  new:        { color:"#a855f7", icon:"★", label:"New"        },
};

/* ─── Shared UI helpers ──────────────────────────────────────────────────── */
function SevBadge({ sev }) {
  const c = SEV_CFG[sev] || SEV_CFG.LOW;
  return (
    <span style={{fontSize:10,fontWeight:800,padding:"2px 8px",borderRadius:4,
      background:c.bg,color:c.color,border:`1px solid ${c.border}`,letterSpacing:0.5}}>
      {sev}
    </span>
  );
}

function ChartTip({ active, payload, label }) {
  const T = useTheme();
  if (!active || !payload?.length) return null;
  return (
    <div style={{background:T.tipBg,border:`1px solid ${T.tipBorder}`,borderRadius:8,padding:"10px 14px",fontSize:12,
      boxShadow:"0 4px 16px rgba(0,0,0,0.15)"}}>
      <div style={{color:T.textSub,marginBottom:5,fontWeight:600}}>{label}</div>
      {payload.map((p,i)=>(
        <div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
          <span style={{width:8,height:8,borderRadius:2,background:p.color,display:"inline-block"}}/>
          <span style={{color:T.textSub}}>{p.name}:</span>
          <span style={{color:T.textHeading,fontWeight:700}}>{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function ScoreRing({ score, size=110 }) {
  const T = useTheme();
  const r = size/2-9, circ = 2*Math.PI*r;
  const color = score>=85?"#22c55e":score>=65?"#3b82f6":"#ef4444";
  return (
    <div style={{position:"relative",width:size,height:size,flexShrink:0}}>
      <svg width={size} height={size} style={{transform:"rotate(-90deg)"}}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={T.border} strokeWidth={7}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={7}
          strokeDasharray={circ} strokeDashoffset={circ-(score/100)*circ} strokeLinecap="round"
          style={{transition:"stroke-dashoffset 1.5s ease",filter:`drop-shadow(0 0 6px ${color})`}}/>
      </svg>
      <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center"}}>
        <span style={{fontSize:size*0.27,fontWeight:800,color,fontFamily:"monospace"}}>{score}</span>
      </div>
    </div>
  );
}

/* ─── User Card (list page) ──────────────────────────────────────────────── */
function UserCard({ user, onClick }) {
  const T = useTheme();
  const t = TREND_CFG[user.trend] || TREND_CFG.stable;
  const scoreColor = user.avg_score>=85?"#22c55e":user.avg_score>=65?"#3b82f6":"#ef4444";
  return (
    <div onClick={onClick} style={{
      background:T.bgCard, border:`1px solid ${T.border}`,
      borderRadius:14, padding:"22px 24px", cursor:"pointer", transition:"all 0.2s",
    }}
    onMouseEnter={e=>e.currentTarget.style.border=`1px solid ${T.borderHover}`}
    onMouseLeave={e=>e.currentTarget.style.border=`1px solid ${T.border}`}
    >
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:16}}>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <div style={{width:44,height:44,borderRadius:12,
            background:"linear-gradient(135deg,#3b82f6,#6366f1)",
            display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,fontWeight:700,color:"#fff"}}>
            {user.username[0].toUpperCase()}
          </div>
          <div>
            <div style={{fontWeight:700,fontSize:15,color:T.textHeading}}>@{user.username}</div>
            <div style={{fontSize:11,color:T.textMuted}}>Since {user.first_seen}</div>
          </div>
        </div>
        <span style={{fontSize:12,fontWeight:600,padding:"4px 12px",borderRadius:20,
          background:`${t.color}18`,color:t.color,border:`1px solid ${t.color}40`}}>
          {t.icon} {t.label}
        </span>
      </div>

      <div style={{display:"flex",alignItems:"center",gap:16,marginBottom:16}}>
        <div style={{textAlign:"center"}}>
          <div style={{fontSize:36,fontWeight:800,fontFamily:"monospace",color:scoreColor,lineHeight:1}}>{user.avg_score}</div>
          <div style={{fontSize:10,color:T.textMuted,marginTop:2}}>avg score</div>
        </div>
        <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
          {[
            ["PRs Reviewed",   user.total_prs,                T.text],
            ["Total Findings", user.total_findings,           T.text],
            ["Critical",       user.severity_counts?.high||0, "#ef4444"],
            ["Last Score",     user.latest_score,             scoreColor],
          ].map(([label,val,color])=>(
            <div key={label} style={{background:T.bgInput,borderRadius:8,padding:"8px 10px"}}>
              <div style={{fontSize:18,fontWeight:800,fontFamily:"monospace",color}}>{val}</div>
              <div style={{fontSize:10,color:T.textMuted}}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
        {Object.entries(user.agent_counts||{}).map(([agent,count])=>(
          <span key={agent} style={{fontSize:10,padding:"2px 8px",borderRadius:4,
            background:"rgba(99,102,241,0.12)",color:"#818cf8",border:"1px solid rgba(99,102,241,0.2)"}}>
            {agent}: {count}
          </span>
        ))}
      </div>
      <div style={{marginTop:14,fontSize:12,color:"#3b82f6",fontWeight:500}}>View full profile →</div>
    </div>
  );
}

/* ══════════════════════ INDIVIDUAL USER DASHBOARD ═══════════════════════════ */
function UserProfile({ username, onBack }) {
  const T = useTheme();
  const [data,       setData]       = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [tab,        setTab]        = useState("overview");
  const [error,      setError]      = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError,   setPdfError]   = useState(null);

  const downloadPDF = async () => {
    setPdfLoading(true); setPdfError(null);
    try {
      const res = await fetch(`${API}/api/report/${username}`);
      if (!res.ok) {
        let detail = `Server error ${res.status}`;
        try { const j = await res.json(); detail = j.detail||j.error||detail; } catch(_) {}
        throw new Error(detail);
      }
      const ct = res.headers.get("content-type")||"";
      if (!ct.includes("application/pdf")) {
        let detail = "Response is not a PDF.";
        try { const j = await res.json(); detail = j.detail||j.error||detail; } catch(_) {}
        throw new Error(detail);
      }
      const blob = await res.blob();
      if (blob.size < 100) throw new Error("Downloaded PDF appears to be empty.");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `RepoGuardian_${username}_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch(e) { setPdfError(e.message); }
    finally { setPdfLoading(false); }
  };

  useEffect(()=>{
    setLoading(true);
    fetch(`${API}/api/user/${username}`)
      .then(r=>r.json()).then(d=>{setData(d);setLoading(false);})
      .catch(e=>{setError(e.message);setLoading(false);});
  },[username]);

  if (loading) return <div style={{textAlign:"center",padding:"80px 0",color:T.textMuted}}>Loading @{username} profile...</div>;
  if (error||data?.error) return <div style={{textAlign:"center",padding:"80px 0",color:"#ef4444"}}>{error||data.error}</div>;

  const t = TREND_CFG[data.trend]||TREND_CFG.stable;
  const scoreColor = data.avg_score>=85?"#22c55e":data.avg_score>=65?"#3b82f6":"#ef4444";
  const TABS = [
    {key:"overview",   label:"Overview",   icon:"◎"},
    {key:"findings",   label:"Findings",   icon:"⚑"},
    {key:"files",      label:"Files",      icon:"📄"},
    {key:"categories", label:"Categories", icon:"◈"},
  ];

  return (
    <div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>

      {/* Top bar */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:20}}>
        <button onClick={onBack} style={{
          background:"transparent", border:`1px solid ${T.border}`,
          color:T.textSub, padding:"6px 14px", borderRadius:8, cursor:"pointer",
          fontSize:12, display:"flex", alignItems:"center", gap:6,
        }}>← All Developers</button>

        <div style={{display:"flex",flexDirection:"column",alignItems:"flex-end",gap:4}}>
          <button onClick={downloadPDF} disabled={pdfLoading} style={{
            display:"flex", alignItems:"center", gap:8,
            background: pdfLoading?"rgba(37,99,235,0.08)":"rgba(37,99,235,0.15)",
            border:"1px solid rgba(37,99,235,0.35)",
            color: pdfLoading?T.textMuted:"#60a5fa",
            padding:"7px 16px", borderRadius:8,
            cursor: pdfLoading?"not-allowed":"pointer",
            fontSize:13, fontWeight:600, transition:"all 0.2s",
          }}>
            {pdfLoading ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                  style={{animation:"spin 1s linear infinite"}}>
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>
                Generating PDF…
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download PDF Report
              </>
            )}
          </button>
          {pdfError && <span style={{fontSize:11,color:"#ef4444"}}>⚠ {pdfError}</span>}
        </div>
      </div>

      {/* Profile Header */}
      <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:14,padding:"24px 28px",marginBottom:20,transition:"background 0.3s"}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",flexWrap:"wrap",gap:16}}>
          <div style={{display:"flex",alignItems:"center",gap:16}}>
            <div style={{width:60,height:60,borderRadius:16,
              background:"linear-gradient(135deg,#3b82f6,#6366f1)",
              display:"flex",alignItems:"center",justifyContent:"center",fontSize:26,fontWeight:800,color:"#fff"}}>
              {username[0].toUpperCase()}
            </div>
            <div>
              <div style={{fontSize:22,fontWeight:800,color:T.textHeading}}>@{username}</div>
              <div style={{fontSize:12,color:T.textMuted,marginTop:2}}>
                Active since {data.first_seen} · Last PR {data.last_seen}
              </div>
              <span style={{fontSize:12,fontWeight:600,padding:"3px 10px",borderRadius:20,marginTop:6,display:"inline-block",
                background:`${t.color}18`,color:t.color,border:`1px solid ${t.color}40`}}>
                {t.icon} {t.label}
              </span>
            </div>
          </div>

          <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
            {[
              ["Avg Score",      data.avg_score,                  scoreColor],
              ["PRs Reviewed",   data.total_prs,                  T.text],
              ["Total Findings", data.total_findings,             T.text],
              ["Critical",       data.severity_counts?.high||0,   "#ef4444"],
              ["Warnings",       data.severity_counts?.medium||0, "#eab308"],
            ].map(([label,val,color])=>(
              <div key={label} style={{background:T.bgInput,borderRadius:10,padding:"12px 16px",textAlign:"center",minWidth:80}}>
                <div style={{fontSize:26,fontWeight:800,fontFamily:"monospace",color,lineHeight:1}}>{val}</div>
                <div style={{fontSize:10,color:T.textMuted,marginTop:4}}>{label}</div>
              </div>
            ))}
          </div>
        </div>

        {data.recurring?.length > 0 && (
          <div style={{marginTop:18,padding:"12px 16px",background:T.recBg,border:`1px solid ${T.recBorder}`,borderRadius:8}}>
            <div style={{fontSize:12,fontWeight:600,color:"#ef4444",marginBottom:8}}>⚠ Recurring Issues (seen 3+ times)</div>
            <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              {data.recurring.map(r=>(
                <span key={r.category} style={{fontSize:11,padding:"3px 10px",borderRadius:20,
                  background:SEV_CFG[r.severity?.toUpperCase()]?.bg||"rgba(107,114,128,0.1)",
                  color:SEV_CFG[r.severity?.toUpperCase()]?.color||"#6b7280",
                  border:`1px solid ${SEV_CFG[r.severity?.toUpperCase()]?.border||"rgba(107,114,128,0.25)"}`}}>
                  {r.category} ({r.count}×)
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div style={{display:"flex",gap:2,marginBottom:20,borderBottom:`1px solid ${T.tabBorder}`}}>
        {TABS.map(({key,label,icon})=>(
          <button key={key} onClick={()=>setTab(key)} style={{
            padding:"8px 18px", borderRadius:"6px 6px 0 0", border:"none", cursor:"pointer",
            fontSize:13, fontWeight:500, background:"transparent",
            color:tab===key?T.textHeading:T.textMuted,
            borderBottom:`2px solid ${tab===key?"#3b82f6":"transparent"}`,
            transition:"color 0.2s",
          }}><span style={{marginRight:5}}>{icon}</span>{label}</button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {tab==="overview" && (
        <div style={{display:"flex",flexDirection:"column",gap:16}}>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
            <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
              <div style={{fontWeight:600,fontSize:14,marginBottom:16,color:T.textSub}}>Score Per Run</div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.score_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.gridStroke}/>
                  <XAxis dataKey="name" tick={{fontSize:10,fill:T.textMuted}} axisLine={false} tickLine={false}/>
                  <YAxis domain={[0,100]} tick={{fontSize:10,fill:T.textMuted}} axisLine={false} tickLine={false}/>
                  <Tooltip content={<ChartTip/>}/>
                  <Line type="monotone" dataKey="score" name="Score" stroke={scoreColor} strokeWidth={2.5}
                    dot={{fill:scoreColor,r:5,strokeWidth:2,stroke:T.bg}} activeDot={{r:7}}/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
              <div style={{fontWeight:600,fontSize:14,marginBottom:16,color:T.textSub}}>Issues Per Run</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.issues_per_pr} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.gridStroke}/>
                  <XAxis dataKey="name" tick={{fontSize:10,fill:T.textMuted}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fontSize:10,fill:T.textMuted}} axisLine={false} tickLine={false}/>
                  <Tooltip content={<ChartTip/>}/>
                  <Bar dataKey="high"   name="High"   stackId="a" fill="#ef4444"/>
                  <Bar dataKey="medium" name="Medium" stackId="a" fill="#eab308"/>
                  <Bar dataKey="low"    name="Low"    stackId="a" fill="#6b7280" radius={[3,3,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
            <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
              <div style={{fontWeight:600,fontSize:14,marginBottom:16,color:T.textSub}}>Code Quality Radar</div>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={data.radar_data} margin={{top:10,right:30,bottom:10,left:30}}>
                  <PolarGrid stroke={T.polarGrid}/>
                  <PolarAngleAxis dataKey="subject" tick={{fill:T.textSub,fontSize:11}}/>
                  <Radar dataKey="A" stroke={scoreColor} fill={scoreColor} fillOpacity={0.15} strokeWidth={2} dot={{fill:scoreColor,r:4}}/>
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
              <div style={{fontWeight:600,fontSize:14,marginBottom:16,color:T.textSub}}>Findings by Agent</div>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={data.agent_pie} cx="50%" cy="50%" outerRadius={75} innerRadius={40} dataKey="value" paddingAngle={3}>
                    {(data.agent_pie||[]).map((e,i)=><Cell key={i} fill={e.color} stroke="transparent"/>)}
                  </Pie>
                  <Tooltip content={<ChartTip/>}/>
                </PieChart>
              </ResponsiveContainer>
              <div style={{display:"flex",flexWrap:"wrap",gap:10,justifyContent:"center",marginTop:8}}>
                {(data.agent_pie||[]).map(({name,color,value})=>(
                  <div key={name} style={{display:"flex",alignItems:"center",gap:5,fontSize:11}}>
                    <span style={{width:8,height:8,borderRadius:2,background:color,display:"inline-block"}}/>
                    <span style={{color:T.textMuted}}>{name}</span>
                    <span style={{color,fontWeight:700,fontFamily:"monospace"}}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:12,padding:"22px 24px"}}>
            <div style={{fontWeight:600,fontSize:14,marginBottom:20,color:T.textSub}}>Severity Breakdown</div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16}}>
              {[
                ["High (Critical)",   data.severity_counts?.high||0,   "#ef4444","Must fix before merge"],
                ["Medium (Warnings)", data.severity_counts?.medium||0, "#eab308","Should fix before release"],
                ["Low (Suggestions)", data.severity_counts?.low||0,    "#6b7280","Nice to fix"],
              ].map(([label,val,color,sub])=>(
                <div key={label} style={{background:T.bgSubtle,borderRadius:10,padding:"18px",textAlign:"center",
                  border:`1px solid ${color}30`}}>
                  <div style={{fontSize:42,fontWeight:800,fontFamily:"monospace",color,lineHeight:1,marginBottom:6}}>{val}</div>
                  <div style={{fontSize:13,fontWeight:600,color:T.textHeading,marginBottom:4}}>{label}</div>
                  <div style={{fontSize:11,color:T.textMuted}}>{sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── FINDINGS ── */}
      {tab==="findings" && (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <div style={{fontSize:13,color:T.textMuted,marginBottom:4}}>
            Showing top {data.findings?.length} issues (sorted by severity)
          </div>
          {(data.findings||[]).map((f,i)=>{
            const sevColor = SEV_CFG[f.severity]?.color||"#6b7280";
            return (
              <div key={f.id} style={{
                background:T.bgCard, border:`1px solid ${T.border}`,
                borderLeft:`3px solid ${sevColor}`, borderRadius:10, padding:"16px 20px",
                animation:`fadeIn 0.3s ease ${i*0.03}s both`,
              }}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    <SevBadge sev={f.severity}/>
                    <span style={{fontSize:10,padding:"2px 8px",borderRadius:4,
                      background:"rgba(139,92,246,0.15)",color:"#a78bfa",
                      border:"1px solid rgba(139,92,246,0.3)"}}>{f.agent}</span>
                    {f.pr_number && <span style={{fontSize:10,color:T.textMuted}}>PR #{f.pr_number}</span>}
                  </div>
                  <span style={{fontSize:11,color:T.textMuted,fontFamily:"monospace"}}>{f.file}:{f.line}</span>
                </div>
                <div style={{fontSize:13,fontWeight:500,color:T.textHeading,marginBottom:8}}>{f.message}</div>
                {f.fix && (
                  <div style={{background:T.fixBg,border:`1px solid ${T.fixBorder}`,
                    borderRadius:6,padding:"8px 12px",fontSize:12,color:T.textSub,fontFamily:"monospace"}}>
                    Fix: {f.fix}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── FILES ── */}
      {tab==="files" && (
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <div style={{fontSize:13,color:T.textMuted,marginBottom:4}}>Files with most issues</div>
          {(data.files_data||[]).map((f)=>{
            const maxIssues = Math.max(...(data.files_data||[]).map(x=>x.total),1);
            const pct = Math.round((f.total/maxIssues)*100);
            return (
              <div key={f.file} style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:10,padding:"16px 20px"}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                  <span style={{fontSize:13,fontWeight:600,color:T.textHeading,fontFamily:"monospace"}}>{f.file}</span>
                  <span style={{fontSize:18,fontWeight:800,fontFamily:"monospace",color:"#3b82f6"}}>{f.total}</span>
                </div>
                <div style={{display:"flex",gap:12,marginBottom:10}}>
                  {[["High",f.high,"#ef4444"],["Medium",f.medium,"#eab308"],["Low",f.low,"#6b7280"]].map(([l,v,c])=>(
                    <span key={l} style={{fontSize:11,color:v>0?c:T.textMuted,fontFamily:"monospace"}}>
                      {l}: <b>{v}</b>
                    </span>
                  ))}
                </div>
                <div style={{height:4,background:T.bgInput,borderRadius:2,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${pct}%`,background:"#3b82f6",borderRadius:2,transition:"width 1s ease"}}/>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── CATEGORIES ── */}
      {tab==="categories" && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:12}}>
          {Object.entries(data.category_counts||{}).sort((a,b)=>b[1]-a[1]).map(([cat,count])=>{
            const maxCount = Math.max(...Object.values(data.category_counts||{}),1);
            const pct = Math.round((count/maxCount)*100);
            const color = count>=20?"#ef4444":count>=10?"#eab308":"#3b82f6";
            return (
              <div key={cat} style={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:10,padding:"14px 18px"}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}>
                  <span style={{fontSize:13,fontWeight:600,color:T.textHeading,textTransform:"capitalize"}}>{cat.replace(/_/g," ")}</span>
                  <span style={{fontSize:18,fontWeight:800,fontFamily:"monospace",color}}>{count}</span>
                </div>
                <div style={{height:4,background:T.bgInput,borderRadius:2,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${pct}%`,background:color,borderRadius:2,transition:"width 1s ease"}}/>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════ ROOT / USERS LIST ════════════════════════════════════ */
export default function UserDashboard() {
  const [users,      setUsers]      = useState([]);
  const [selected,   setSelected]   = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dark,       setDark]       = useState(true);   // night mode default

  const T = dark ? DARK : LIGHT;

  const fetchUsers = () => {
    fetch(`${API}/api/users`)
      .then(r=>r.json())
      .then(d=>{setUsers(d.users||[]);setLoading(false);setError(null);setLastUpdate(new Date().toLocaleTimeString());})
      .catch(()=>{setError("Cannot reach API — is receiver.py running on port 8000?");setLoading(false);});
  };

  useEffect(()=>{
    fetchUsers();
    const iv = setInterval(fetchUsers, 30000);
    return ()=>clearInterval(iv);
  },[]);

  return (
    <ThemeContext.Provider value={T}>
      <div style={{
        minHeight:"100vh", background:T.bg, color:T.text,
        fontFamily:"'Inter','Segoe UI',sans-serif",
        transition:"background 0.3s, color 0.3s",
      }}>
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
          *{box-sizing:border-box;margin:0;padding:0;}
          ::-webkit-scrollbar{width:4px;}
          ::-webkit-scrollbar-thumb{background:${T.scrollThumb};border-radius:2px;}
          @keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
          @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.35}}
        `}</style>

        {/* Navbar */}
        <nav style={{
          display:"flex", alignItems:"center", justifyContent:"space-between",
          padding:"0 24px", height:62, background:T.nav,
          borderBottom:`1px solid ${T.navBorder}`,
          position:"sticky", top:0, zIndex:100,
          transition:"background 0.3s, border-color 0.3s",
        }}>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:34,height:34,borderRadius:8,
              background:"linear-gradient(135deg,#3b82f6,#6366f1)",
              display:"flex",alignItems:"center",justifyContent:"center",fontSize:17}}>🛡</div>
            <div>
              <div style={{fontWeight:700,fontSize:15,color:T.textHeading}}>RepoGuardian</div>
              <div style={{fontSize:10,color:T.textMuted}}>Developer Profiles</div>
            </div>
          </div>

          <div style={{display:"flex",alignItems:"center",gap:10}}>
            {error ? (
              <div style={{display:"flex",alignItems:"center",gap:6,background:T.errBg,
                border:`1px solid ${T.errBorder}`,padding:"4px 12px",borderRadius:20}}>
                <span style={{width:7,height:7,borderRadius:"50%",background:"#ef4444",display:"inline-block"}}/>
                <span style={{fontSize:12,color:"#ef4444",fontWeight:600}}>Offline</span>
              </div>
            ) : (
              <div style={{display:"flex",alignItems:"center",gap:6,background:"rgba(34,197,94,0.08)",
                border:"1px solid rgba(34,197,94,0.2)",padding:"4px 12px",borderRadius:20}}>
                <span style={{width:7,height:7,borderRadius:"50%",background:"#22c55e",
                  display:"inline-block",animation:"pulse 2s infinite"}}/>
                <span style={{fontSize:12,color:"#22c55e",fontWeight:600}}>
                  Live {lastUpdate&&`· ${lastUpdate}`}
                </span>
              </div>
            )}

            {/* ☀️/🌙 Theme toggle */}
            <ThemeToggle dark={dark} onToggle={()=>setDark(d=>!d)}/>

            <a href="http://localhost:5173" style={{
              fontSize:12, color:T.textMuted, textDecoration:"none",
              padding:"4px 12px", borderRadius:6, border:`1px solid ${T.border}`,
            }}>← Main Dashboard</a>
          </div>
        </nav>

        <div style={{padding:"24px",maxWidth:1200,margin:"0 auto"}}>
          {loading && !error && (
            <div style={{textAlign:"center",padding:"80px 0",color:T.textMuted}}>
              Loading developer profiles from memory store...
            </div>
          )}

          {error && (
            <div style={{background:T.errBg,border:`1px solid ${T.errBorder}`,
              borderRadius:8,padding:"12px 16px",fontSize:13,color:"#fca5a5",marginBottom:20}}>
              ⚠ {error}
            </div>
          )}

          {!loading && !selected && (
            <div style={{animation:"fadeIn 0.3s ease"}}>
              <div style={{marginBottom:24}}>
                <h1 style={{fontSize:24,fontWeight:800,color:T.textHeading,marginBottom:6}}>Developer Profiles</h1>
                <p style={{fontSize:13,color:T.textMuted}}>
                  {users.length} developer{users.length!==1?"s":""} tracked · Click any card to view full profile
                </p>
              </div>

              {users.length===0 ? (
                <div style={{textAlign:"center",padding:"80px 0",color:T.textMuted,fontSize:14}}>
                  No developers tracked yet. Run the orchestrator on a PR first.
                </div>
              ) : (
                <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(380px,1fr))",gap:20}}>
                  {users.map(user=>(
                    <UserCard key={user.username} user={user} onClick={()=>setSelected(user.username)}/>
                  ))}
                </div>
              )}
            </div>
          )}

          {!loading && selected && (
            <div style={{animation:"fadeIn 0.3s ease"}}>
              <UserProfile username={selected} onBack={()=>setSelected(null)}/>
            </div>
          )}
        </div>
      </div>
    </ThemeContext.Provider>
  );
}