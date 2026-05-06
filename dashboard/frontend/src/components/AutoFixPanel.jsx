import { useState } from "react";

const FIXES = [

  {
    risk: "Hardcoded Secret",
    severity: "Critical",
    file: "config/auth.js",

    before:
`const API_KEY = "sk_live_secret_123";`,

    after:
`const API_KEY = process.env.API_KEY;`,

    explanation:
      "Moved sensitive credential into protected environment variable storage."
  },

  {
    risk: "SQL Injection",
    severity: "High",
    file: "db/query.py",

    before:
`query = "SELECT * FROM users WHERE id=" + userId`,

    after:
`query = "SELECT * FROM users WHERE id=%s"`,

    explanation:
      "Parameterized query prevents attacker-controlled SQL execution."
  },

  {
    risk: "Open API Access",
    severity: "Medium",
    file: "api/routes.js",

    before:
`app.use("/admin", adminRouter);`,

    after:
`app.use("/admin", authMiddleware, adminRouter);`,

    explanation:
      "Authentication middleware added to secure sensitive endpoints."
  }

];

export default function AutoFixPanel() {

  const [selected, setSelected] = useState(FIXES[0]);

  const [applied, setApplied] = useState(false);

  const [showPR, setShowPR] = useState(false);

  const [prData, setPrData] = useState(null);

  return (

    <div style={{
      background: "#161b22",
      border: "1px solid #30363d",
      borderRadius: "16px",
      overflow: "hidden",
      position: "relative"
    }}>

      {/* Header */}
      <div style={{
        padding: "18px",
        borderBottom: "1px solid #21262d",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>

        <div>

          <div style={{
            color: "white",
            fontWeight: 700,
            fontSize: "20px"
          }}>
            ⚡ AI Auto Remediation
          </div>

          <div style={{
            color: "#8b949e",
            marginTop: "6px",
            fontSize: "13px"
          }}>
            AI-generated secure remediation workflow
          </div>

        </div>

        <div style={{
          background: "#23863622",
          color: "#3fb950",
          padding: "6px 12px",
          borderRadius: "999px",
          fontSize: "12px",
          fontWeight: 600
        }}>
          AI Enabled
        </div>

      </div>

      {/* Main */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "260px 1fr"
      }}>

        {/* Left Risks */}
        <div style={{
          borderRight: "1px solid #21262d",
          padding: "12px"
        }}>

          {FIXES.map((fix, idx) => (

            <div
              key={idx}
              onClick={() => {

                setSelected(fix);
                setApplied(false);

              }}
              style={{
                padding: "14px",
                marginBottom: "10px",
                borderRadius: "10px",
                cursor: "pointer",
                background:
                  selected.risk === fix.risk
                    ? "#1f2937"
                    : "#0d1117",

                border:
                  selected.risk === fix.risk
                    ? "1px solid #58a6ff"
                    : "1px solid #21262d"
              }}
            >

              <div style={{
                color: "white",
                fontWeight: 600,
                marginBottom: "6px"
              }}>
                {fix.risk}
              </div>

              <div style={{
                color:
                  fix.severity === "Critical"
                    ? "#ff4d4f"
                    : fix.severity === "High"
                    ? "#e3b341"
                    : "#d29922",

                fontSize: "12px"
              }}>
                {fix.severity}
              </div>

            </div>

          ))}

        </div>

        {/* Right */}
        <div style={{
          padding: "20px"
        }}>

          <div style={{
            color: "#58a6ff",
            marginBottom: "16px",
            fontSize: "13px"
          }}>
            {selected.file}
          </div>

          {/* Before */}
          <div style={{
            marginBottom: "20px"
          }}>

            <div style={{
              color: "#ff7b72",
              marginBottom: "8px",
              fontWeight: 600
            }}>
              ❌ Vulnerable Code
            </div>

            <pre style={{
              background: "#0d1117",
              padding: "16px",
              borderRadius: "10px",
              overflowX: "auto",
              color: "#ff7b72",
              border: "1px solid #30363d"
            }}>
{selected.before}
            </pre>

          </div>

          {/* After */}
          <div style={{
            marginBottom: "20px"
          }}>

            <div style={{
              color: "#3fb950",
              marginBottom: "8px",
              fontWeight: 600
            }}>
              ✅ AI Suggested Fix
            </div>

            <pre style={{
              background: "#0d1117",
              padding: "16px",
              borderRadius: "10px",
              overflowX: "auto",
              color: "#3fb950",
              border: "1px solid #30363d"
            }}>
{selected.after}
            </pre>

          </div>

          {/* Explanation */}
          <div style={{
            background: "#0d1117",
            border: "1px solid #21262d",
            padding: "16px",
            borderRadius: "10px",
            color: "#c9d1d9",
            lineHeight: "1.7",
            marginBottom: "20px"
          }}>
            {selected.explanation}
          </div>

          {/* Buttons */}
          <div style={{
            display: "flex",
            gap: "12px"
          }}>

            <button
              onClick={() => setApplied(true)}
              style={{
                background: "#238636",
                border: "none",
                color: "white",
                padding: "12px 18px",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 600
              }}
            >
              ⚡ Apply AI Fix
            </button>

            <button
              onClick={async () => {

                try {

                  const res = await fetch(
                    "http://localhost:8000/api/create-pr",
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json"
                      },
                      body: JSON.stringify({
                        risk: selected.risk,
                        fix: selected.after
                      })
                    }
                  );

                  const data = await res.json();

                  console.log(data);

                  if (data.success) {

                    setPrData(data);

                    setShowPR(true);

                  } else {

                    alert(
                      `❌ PR Creation Failed\n\n${data.error}`
                    );

                  }

                } catch (err) {

                  console.error(err);

                  alert("Backend connection failed");

                }

              }}
              style={{
                background: "#21262d",
                border: "1px solid #30363d",
                color: "white",
                padding: "12px 18px",
                borderRadius: "8px",
                cursor: "pointer"
              }}
            >
              Create Secure PR
            </button>

          </div>

          {/* Success */}
          {applied && (

            <div style={{
              marginTop: "20px",
              background: "#23863622",
              border: "1px solid #238636",
              padding: "14px",
              borderRadius: "10px",
              color: "#3fb950"
            }}>
              ✅ AI remediation applied successfully.
            </div>

          )}

        </div>

      </div>

      {/* PR Modal */}
      {showPR && (

        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.75)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 9999
        }}>

          <div style={{
            width: "700px",
            background: "#161b22",
            border: "1px solid #30363d",
            borderRadius: "16px",
            overflow: "hidden"
          }}>

            <div style={{
              padding: "18px 24px",
              borderBottom: "1px solid #21262d"
            }}>

              <div style={{
                color: "white",
                fontWeight: 700,
                fontSize: "20px"
              }}>
                ✅ Secure Pull Request Created
              </div>

              <div style={{
                color: "#8b949e",
                marginTop: "6px",
                fontSize: "13px"
              }}>
                AI-generated remediation PR ready for merge
              </div>

            </div>

            <div style={{
              padding: "24px"
            }}>

              <div style={{
                marginBottom: "18px"
              }}>

                <div style={{
                  color: "#8b949e",
                  fontSize: "12px",
                  marginBottom: "6px"
                }}>
                  PR TITLE
                </div>

                <div style={{
                  color: "#58a6ff",
                  fontWeight: 600,
                  fontSize: "16px"
                }}>
                  {prData?.title}
                </div>

              </div>

              <button
                onClick={() => {
                  window.open(prData?.url, "_blank");
                }}
                style={{
                  background: "#1f6feb",
                  border: "none",
                  color: "white",
                  padding: "12px 20px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontWeight: 600,
                  marginRight: "12px"
                }}
              >
                Open GitHub PR
              </button>

              <button
                onClick={async () => {

                  try {

                    const response = await fetch(
                      "http://localhost:8000/api/merge-pr",
                      {
                        method: "POST",
                        headers: {
                          "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                          pr_number: prData.number
                        })
                      }
                    );

                    const data = await response.json();

                    if (data.success) {

                      alert("✅ Pull Request Merged");

                      setShowPR(false);

                    } else {

                      alert(`❌ Merge Failed\n\n${data.error}`);

                    }

                  } catch (err) {

                    console.error(err);

                    alert("Merge API failed");

                  }

                }}
                style={{
                  background: "#238636",
                  border: "none",
                  color: "white",
                  padding: "12px 20px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontWeight: 600
                }}
              >
                Merge Secure PR
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}