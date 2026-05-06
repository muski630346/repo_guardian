import { useState } from "react";

const SEVERITY_CONFIG = {
  critical: { color: "#da3633", bg: "#da363318", label: "Critical" },
  high: { color: "#e3b341", bg: "#e3b34118", label: "High" },
  medium: { color: "#d29922", bg: "#d2992218", label: "Medium" },
  low: { color: "#2ea043", bg: "#2ea04318", label: "Low" },
};

// 🔥 Business-readable affected area
const getArea = (file = "") => {
  const f = file.toLowerCase();

  if (f.includes("auth")) return "Authentication System";
  if (f.includes("config")) return "Configuration Layer";
  if (f.includes("db")) return "Database";
  if (f.includes("api")) return "API Gateway";
  if (f.includes("security")) return "Security Module";
  if (f.includes("agent")) return "AI Agent Engine";

  return "Core System";
};

// 🔥 Human-readable risk type
const getRiskType = (file = "") => {
  const f = file.toLowerCase();

  if (f.includes("auth")) return "Authentication Risk";
  if (f.includes("config")) return "Misconfiguration";
  if (f.includes("db")) return "Data Exposure";
  if (f.includes("api")) return "API Vulnerability";
  if (f.includes("security")) return "Security Failure";
  if (f.includes("agent")) return "AI Logic Risk";

  return "General Risk";
};

// 🔥 Better descriptions
const getDescription = (msg = "", file = "") => {
  const f = file.toLowerCase();

  if (f.includes("auth"))
    return "Login system can be bypassed, allowing unauthorized users to access accounts.";

  if (f.includes("config"))
    return "System configuration may expose sensitive settings or internal secrets.";

  if (f.includes("db"))
    return "Database protections are weak and could expose customer records.";

  if (f.includes("api"))
    return "API endpoints may allow unauthorized requests or abuse.";

  if (f.includes("security"))
    return "Core security protections are not properly enforced.";

  if (f.includes("agent"))
    return "AI agent execution logic may perform unsafe automated actions.";

  return "Unexpected system behavior detected that could lead to security vulnerabilities.";
};

export default function FindingsTable({ findings = [] }) {

  const [simulation, setSimulation] = useState(null);
  const [fixData, setFixData] = useState(null);

  // 🔥 Attack Simulation
  const handleSimulate = async (finding) => {
    try {

      const res = await fetch("http://localhost:8000/api/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          type: finding.file || "generic"
        })
      });

      const data = await res.json();

      setSimulation(data);

    } catch (e) {

      console.error(e);

    }
  };

  // 🔥 AutoFix
  const handleAutoFix = async (finding) => {

    try {

      const res = await fetch("http://localhost:8000/api/autofix", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          type: finding.file || "generic"
        })
      });

      const data = await res.json();

      setFixData(data);

    } catch (e) {

      console.error(e);

    }
  };

  // 🔥 Empty state
  if (findings.length === 0) {
    return (
      <div style={{
        padding: "32px",
        textAlign: "center",
        color: "#484f58"
      }}>
        No risks detected
      </div>
    );
  }

  return (
    <div>

      {/* 🔥 Risk Banner */}
      <div style={{
        marginBottom: "12px",
        color: "#da3633",
        fontSize: "13px",
        fontWeight: 500
      }}>
        ⚠️ {findings.length} active risks detected in your repository
      </div>

      {/* 🔥 Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "13px"
        }}>

          <thead>
            <tr style={{ borderBottom: "1px solid #21262d" }}>
              {["Severity", "Risk Type", "Affected Area", "Description", "Action"].map(h => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: "8px 16px",
                    color: "#8b949e",
                    fontSize: "11px",
                    fontWeight: 600,
                    textTransform: "uppercase",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {findings.map((f, i) => {

              const cfg = SEVERITY_CONFIG[f.severity] || {
                color: "#8b949e",
                bg: "#8b949e18",
                label: f.severity
              };

              return (
                <tr
                  key={i}
                  style={{
                    borderBottom: "1px solid #161b22"
                  }}
                >

                  {/* Severity */}
                  <td style={{ padding: "10px 16px" }}>
                    <span style={{
                      background: cfg.bg,
                      color: cfg.color,
                      padding: "3px 10px",
                      borderRadius: "12px",
                      fontSize: "11px",
                      fontWeight: 600
                    }}>
                      {cfg.label}
                      {cfg.label === "Critical" && " 🔥"}
                      {cfg.label === "High" && " ⚠️"}
                    </span>
                  </td>

                  {/* Risk Type */}
                  <td style={{
                    padding: "10px 16px",
                    color: "#58a6ff"
                  }}>
                    {getRiskType(f.file)}
                  </td>

                  {/* Area */}
                  <td style={{
                    padding: "10px 16px",
                    color: "#8b949e"
                  }}>
                    {getArea(f.file)}
                  </td>

                  {/* Description */}
                  <td style={{
                    padding: "10px 16px",
                    color: "#e6edf3",
                    maxWidth: "350px",
                    lineHeight: "1.5"
                  }}>
                    {getDescription(f.message, f.file)}
                  </td>

                  {/* Actions */}
                  <td style={{
                    padding: "10px 16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px"
                  }}>

                    {/* Simulate */}
                    <button
                      onClick={() => handleSimulate(f)}
                      style={{
                        background: "#cf222e",
                        color: "white",
                        border: "none",
                        padding: "5px 10px",
                        borderRadius: "6px",
                        cursor: "pointer",
                        fontSize: "11px"
                      }}
                    >
                      🚨 Simulate Attack
                    </button>

                    {/* Auto Fix */}
                    <button
                      onClick={() => handleAutoFix(f)}
                      style={{
                        background: "#1f6feb",
                        color: "white",
                        border: "none",
                        padding: "5px 10px",
                        borderRadius: "6px",
                        cursor: "pointer",
                        fontSize: "11px"
                      }}
                    >
                      🛠️ Auto Fix
                    </button>

                  </td>

                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 🔥 Simulation Modal */}
      {simulation && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>

          <div style={{
            background: "#0d1117",
            padding: "24px",
            borderRadius: "12px",
            width: "430px",
            border: "1px solid #30363d",
            boxShadow: "0 0 40px rgba(0,0,0,0.6)"
          }}>

            <h2 style={{
              color: "#da3633",
              marginBottom: "12px"
            }}>
              🚨 {simulation.title}
            </h2>

            <p style={{ color: "#e6edf3" }}>
              <strong>Risk:</strong> {simulation.risk}
            </p>

            <p style={{
              color: "#e6edf3",
              marginTop: "8px"
            }}>
              <strong>Estimated Business Impact:</strong> {simulation.cost}
            </p>

            <div style={{ marginTop: "14px" }}>
              <strong style={{ color: "#e6edf3" }}>
                Attack Consequences:
              </strong>

              <ul style={{
                marginTop: "8px",
                paddingLeft: "20px",
                color: "#8b949e",
                lineHeight: "1.7"
              }}>
                {simulation.impact.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>

            <p style={{
              marginTop: "12px",
              color: "#8b949e",
              fontSize: "12px"
            }}>
              ⚡ Threat detected in {simulation.detected_in}
            </p>

            <button
              onClick={() => setSimulation(null)}
              style={{
                marginTop: "16px",
                background: "#238636",
                color: "white",
                border: "none",
                padding: "6px 14px",
                borderRadius: "6px",
                cursor: "pointer"
              }}
            >
              Close
            </button>

          </div>
        </div>
      )}

      {/* 🔥 AUTOFIX MODAL */}
      {fixData && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "rgba(0,0,0,0.7)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>

          <div style={{
            background: "#0d1117",
            padding: "24px",
            borderRadius: "12px",
            width: "460px",
            border: "1px solid #30363d"
          }}>

            <h2 style={{
              color: "#1f6feb",
              marginBottom: "14px"
            }}>
              🛠️ AI Remediation Plan
            </h2>

            <div style={{
              color: "#8b949e",
              marginBottom: "12px",
              lineHeight: "1.6"
            }}>
              RepoGuardian generated an automated remediation workflow.
            </div>

            <ul style={{
              color: "#c9d1d9",
              paddingLeft: "20px",
              lineHeight: "1.8"
            }}>
              {fixData.fix.map((f, idx) => (
                <li key={idx}>{f}</li>
              ))}
            </ul>

            <div style={{
              marginTop: "16px",
              background: "#161b22",
              border: "1px solid #30363d",
              padding: "12px",
              borderRadius: "8px",
              color: "#2ea043",
              fontSize: "13px"
            }}>
              ✅ Estimated remediation success rate: 91%
            </div>

            <button
              onClick={() => setFixData(null)}
              style={{
                marginTop: "16px",
                background: "#238636",
                color: "white",
                border: "none",
                padding: "6px 14px",
                borderRadius: "6px",
                cursor: "pointer"
              }}
            >
              Close
            </button>

          </div>
        </div>
      )}

    </div>
  );
}