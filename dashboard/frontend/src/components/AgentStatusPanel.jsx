export default function AgentStatusPanel({ agents = [] }) {
  if (agents.length === 0) {
    return <p style={{ color: "#484f58", fontSize: "12px" }}>No agents running.</p>;
  }

  const statusConfig = {
    running: { color: "#d29922", glow: true,  icon: "⏳" },
    done:    { color: "#2ea043", glow: false, icon: "✅" },
    error:   { color: "#da3633", glow: false, icon: "❌" },
    idle:    { color: "#484f58", glow: false, icon: "○"  },
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
      {agents.map((a) => {
        const cfg = statusConfig[a.status] || statusConfig.idle;
        return (
          <div key={a.name} style={{
            display: "flex", alignItems: "center", gap: "7px",
            background: "#0d1117", border: "1px solid #21262d",
            borderRadius: "6px", padding: "6px 12px", fontSize: "12px",
          }}>
            <span style={{
              width: "6px", height: "6px", borderRadius: "50%",
              background: cfg.color,
              boxShadow: cfg.glow ? `0 0 6px ${cfg.color}` : "none",
              display: "inline-block",
            }} />
            <span style={{ color: "#c9d1d9", fontFamily: "monospace" }}>{a.name}</span>
            <span style={{ color: cfg.color, fontSize: "10px" }}>{a.status}</span>
          </div>
        );
      })}
    </div>
  );
}