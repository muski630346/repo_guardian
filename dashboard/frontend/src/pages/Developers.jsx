import VoiceCopilot from "../components/VoiceCopilot";

const developers = [
  {
    name: "muski630346",
    role: "Repository Owner",
    risk: "MEDIUM",
    health: "92/100",
    issue: "hardcoded secrets",
    mistakes: 12,
    trend: "improving",
    scores: "62 → 70 → 81 → 84",
    trust: "87%",
  },
  {
    name: "codewithVamshi5",
    role: "Core Contributor",
    risk: "LOW",
    health: "88/100",
    issue: "unsafe imports",
    mistakes: 4,
    trend: "stable",
    scores: "72 → 76 → 81 → 84",
    trust: "91%",
  },
  {
    name: "AkshithaSaada",
    role: "Security Contributor",
    risk: "LOW",
    health: "90/100",
    issue: "dependency exposure",
    mistakes: 3,
    trend: "improving",
    scores: "68 → 74 → 82 → 89",
    trust: "93%",
  },
  {
    name: "KesaramSnigdhaReddy",
    role: "Repository Contributor",
    risk: "LOW",
    health: "86/100",
    issue: "permission misconfig",
    mistakes: 5,
    trend: "stable",
    scores: "70 → 73 → 79 → 84",
    trust: "89%",
  },
];

export default function Developers() {
  return (
    <div style={{ position: "relative" }}>
      <div style={{ marginBottom: "35px" }}>
        <h1
          style={{
            color: "#ff9d2f",
            fontSize: "42px",
            fontWeight: "800",
            marginBottom: "10px",
            letterSpacing: "1px",
          }}
        >
          Developer Security Intelligence
        </h1>

        <p
          style={{
            color: "#9ca3af",
            fontSize: "16px",
            maxWidth: "900px",
            lineHeight: "1.8",
          }}
        >
          Behavioral profiling, contributor security analytics, repository
          collaboration intelligence, recurring vulnerability detection, and
          autonomous AI-driven developer risk assessment.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "30px",
        }}
      >
        {developers.map((dev, index) => (
          <div
            key={index}
            style={{
              background: "#050816",
              border: "1px solid rgba(255,140,0,0.18)",
              borderRadius: "26px",
              padding: "34px",
              boxShadow: "0 0 40px rgba(255,120,0,0.08)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                top: "-100px",
                right: "-100px",
                width: "240px",
                height: "240px",
                background:
                  "radial-gradient(circle, rgba(255,140,0,0.12), transparent 70%)",
              }}
            />

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "30px",
                flexWrap: "wrap",
                gap: "20px",
              }}
            >
              <div style={{ display: "flex", gap: "18px" }}>
                <div
                  style={{
                    width: "72px",
                    height: "72px",
                    borderRadius: "50%",
                    background:
                      "linear-gradient(135deg,#ff7b00,#ffb347)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "30px",
                    fontWeight: "800",
                    color: "#fff",
                    boxShadow: "0 0 25px rgba(255,140,0,0.5)",
                  }}
                >
                  {dev.name[0].toUpperCase()}
                </div>

                <div>
                  <h2
                    style={{
                      color: "#fff",
                      fontSize: "34px",
                      marginBottom: "8px",
                      fontWeight: "800",
                    }}
                  >
                    {dev.name}
                  </h2>

                  <p
                    style={{
                      color: "#94a3b8",
                      fontSize: "15px",
                    }}
                  >
                    {dev.role} • Behavioral Profile Active
                  </p>
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <p
                  style={{
                    color: "#9ca3af",
                    fontSize: "14px",
                    marginBottom: "10px",
                  }}
                >
                  Behavioral Risk
                </p>

                <h2
                  style={{
                    color:
                      dev.risk === "LOW"
                        ? "#22c55e"
                        : dev.risk === "MEDIUM"
                        ? "#f59e0b"
                        : "#ef4444",
                    fontSize: "46px",
                    margin: 0,
                    fontWeight: "900",
                  }}
                >
                  {dev.risk}
                </h2>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit,minmax(220px,1fr))",
                gap: "20px",
              }}
            >
              {[
                {
                  title: "Security Health",
                  value: dev.health,
                  color: "#22c55e",
                },
                {
                  title: "Top Recurring Issue",
                  value: dev.issue,
                  color: "#ff6b6b",
                },
                {
                  title: "Repeated Mistakes",
                  value: dev.mistakes,
                  color: "#facc15",
                },
                {
                  title: "Trend",
                  value: dev.trend,
                  color: "#60a5fa",
                },
                {
                  title: "Last 5 Scores",
                  value: dev.scores,
                  color: "#c084fc",
                },
                {
                  title: "Trust Score",
                  value: dev.trust,
                  color: "#38bdf8",
                },
              ].map((item, i) => (
                <div
                  key={i}
                  style={{
                    background: "#020617",
                    border: "1px solid rgba(255,140,0,0.12)",
                    borderRadius: "20px",
                    padding: "24px",
                    minHeight: "150px",
                    boxShadow:
                      "inset 0 0 20px rgba(255,120,0,0.04)",
                  }}
                >
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "14px",
                      marginBottom: "16px",
                    }}
                  >
                    {item.title}
                  </p>

                  <h2
                    style={{
                      color: item.color,
                      fontSize: "22px",
                      lineHeight: "1.5",
                      fontWeight: "800",
                      margin: 0,
                    }}
                  >
                    {item.value}
                  </h2>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <VoiceCopilot />
    </div>
  );
}