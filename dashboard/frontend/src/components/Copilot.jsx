import { useState } from "react";

export default function Copilot() {

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const generateAnswer = (q) => {

    const text = q.toLowerCase();

    if (text.includes("auth") || text.includes("login")) {
      return `Authentication vulnerabilities may allow attackers to bypass login systems and gain unauthorized access.

Recommended Actions:
• Enable MFA
• Apply RBAC permissions
• Enforce token expiration
• Monitor failed login attempts`;
    }

    if (text.includes("api")) {
      return `API vulnerabilities may expose sensitive endpoints to malicious requests.

Recommended Actions:
• Enable API authentication
• Add rate limiting
• Validate request payloads
• Restrict public endpoints`;
    }

    if (text.includes("database") || text.includes("db")) {
      return `Database exposure risks may leak customer or internal business data.

Recommended Actions:
• Encrypt sensitive fields
• Rotate credentials
• Restrict database access
• Enable audit logs`;
    }

    if (text.includes("fix") || text.includes("remediate")) {
      return `RepoGuardian AI recommends:

• Rotate exposed secrets
• Apply least privilege access
• Patch vulnerable dependencies
• Enable monitoring
• Remove hardcoded credentials`;
    }

    if (text.includes("critical") || text.includes("priority")) {
      return `Critical remediation priority:

1. Authentication vulnerabilities
2. Database exposure
3. API weaknesses
4. Configuration issues

Critical threats should be fixed immediately.`;
    }

    return `RepoGuardian AI detected security posture weaknesses requiring investigation.

Recommended next steps:
• Review critical findings
• Run remediation workflow
• Export compliance reports
• Patch exposed services`;
  };

  const askAI = () => {

    if (!question.trim()) return;

    setLoading(true);

    const userQuestion = question;

    setMessages(prev => [
      ...prev,
      {
        type: "user",
        text: userQuestion
      }
    ]);

    setQuestion("");

    setTimeout(() => {

      setMessages(prev => [
        ...prev,
        {
          type: "ai",
          text: generateAnswer(userQuestion)
        }
      ]);

      setLoading(false);

    }, 700);
  };

  return (
    <>

      {/* Animation */}

      <style>
        {`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.96);
          }
          to {
            opacity: 1;
            transform: translateY(0px) scale(1);
          }
        }
        `}
      </style>

      {/* Floating AI Button */}

      <button
        onClick={() => setOpen(!open)}
        style={{
          position: "fixed",

          bottom: "18px",
          right: "18px",

          width: "58px",
          height: "58px",

          borderRadius: "50%",

          border:
            "1px solid rgba(255,140,66,0.28)",

          background:
            "linear-gradient(145deg,#0a0a0a,#181818)",

          color: "#ff9d2e",

          fontSize: "24px",

          cursor: "pointer",

          zIndex: 9999,

          boxShadow:
            "0 0 24px rgba(255,140,66,0.18)",

          transition: "0.3s ease",
        }}
      >
        🤖
      </button>

      {/* AI Panel */}

      {open && (

        <div
          style={{
            position: "fixed",

            bottom: "86px",
            right: "18px",

            width: "340px",
            height: "460px",

            background:
              "linear-gradient(145deg,#050505ee,#121212ee)",

            border:
              "1px solid rgba(255,140,66,0.18)",

            borderRadius: "20px",

            overflow: "hidden",

            zIndex: 1000,

            boxShadow:
              "0 0 40px rgba(0,0,0,0.65)",

            display: "flex",

            flexDirection: "column",

            animation: "slideUp 0.2s ease-out",

            backdropFilter: "blur(14px)",
          }}
        >

          {/* Header */}

          <div
            style={{
              padding: "14px 16px",

              borderBottom:
                "1px solid rgba(255,140,66,0.12)",

              display: "flex",

              alignItems: "center",

              justifyContent: "space-between",

              background:
                "linear-gradient(90deg, rgba(255,140,66,0.08), transparent)",
            }}
          >

            <div>

              <div
                style={{
                  color: "#ff9d2e",

                  fontWeight: 700,

                  fontSize: "14px",
                }}
              >
                🤖 RepoGuardian AI
              </div>

              <div
                style={{
                  color: "#8b949e",

                  fontSize: "10px",

                  marginTop: "2px",
                }}
              >
                enterprise security copilot
              </div>

            </div>

            <button
              onClick={() => setOpen(false)}
              style={{
                background: "transparent",

                border: "none",

                color: "#8b949e",

                cursor: "pointer",

                fontSize: "16px",
              }}
            >
              ✕
            </button>

          </div>

          {/* Messages */}

          <div
            style={{
              flex: 1,

              overflowY: "auto",

              padding: "14px",

              display: "flex",

              flexDirection: "column",

              gap: "12px",
            }}
          >

            {messages.length === 0 && (

              <div
                style={{
                  color: "#b6b6b6",

                  fontSize: "12px",

                  lineHeight: "1.9",

                  background:
                    "linear-gradient(145deg,#0d0d0d,#151515)",

                  border:
                    "1px solid rgba(255,140,66,0.10)",

                  borderRadius: "14px",

                  padding: "14px",
                }}
              >

                Ask RepoGuardian AI about:

                <br /><br />

                • authentication risks
                <br />
                • API vulnerabilities
                <br />
                • database exposure
                <br />
                • remediation priority
                <br />
                • compliance analysis

              </div>
            )}

            {messages.map((m, idx) => (

              <div key={idx}>

                {m.type === "user" ? (

                  <div
                    style={{
                      background:
                        "linear-gradient(135deg,#ff7a00,#ff9d2e)",

                      color: "white",

                      padding: "12px 14px",

                      borderRadius: "14px",

                      maxWidth: "85%",

                      marginLeft: "auto",

                      fontSize: "12px",

                      lineHeight: "1.6",

                      boxShadow:
                        "0 0 16px rgba(255,140,66,0.22)",
                    }}
                  >
                    {m.text}
                  </div>

                ) : (

                  <div
                    style={{
                      background:
                        "linear-gradient(145deg,#0a0a0a,#151515)",

                      border:
                        "1px solid rgba(255,140,66,0.10)",

                      color: "#e5e7eb",

                      padding: "14px",

                      borderRadius: "14px",

                      fontSize: "12px",

                      lineHeight: "1.8",

                      whiteSpace: "pre-line",

                      boxShadow:
                        "0 0 16px rgba(0,0,0,0.25)",
                    }}
                  >
                    {m.text}
                  </div>

                )}

              </div>

            ))}

            {loading && (

              <div
                style={{
                  background:
                    "linear-gradient(145deg,#0a0a0a,#151515)",

                  border:
                    "1px solid rgba(255,140,66,0.10)",

                  color: "#ffb066",

                  padding: "12px",

                  borderRadius: "12px",

                  fontSize: "12px",
                }}
              >
                RepoGuardian AI analyzing threat posture...
              </div>
            )}

          </div>

          {/* Suggestions */}

          <div
            style={{
              padding: "0 12px 8px 12px",

              display: "flex",

              flexWrap: "wrap",

              gap: "6px",
            }}
          >

            {[
              "auth risk",
              "API vulnerabilities",
              "database exposure",
              "remediation priority"
            ].map((item, idx) => (

              <button
                key={idx}
                onClick={() => setQuestion(item)}
                style={{
                  background:
                    "linear-gradient(145deg,#0d0d0d,#161616)",

                  border:
                    "1px solid rgba(255,140,66,0.12)",

                  color: "#ffb066",

                  padding: "6px 10px",

                  borderRadius: "999px",

                  fontSize: "10px",

                  cursor: "pointer",

                  transition: "0.2s ease",
                }}
              >
                {item}
              </button>

            ))}

          </div>

          {/* Input */}

          <div
            style={{
              padding: "12px",

              borderTop:
                "1px solid rgba(255,140,66,0.08)",
            }}
          >

            <input
              value={question}
              onChange={(e) =>
                setQuestion(e.target.value)
              }
              placeholder="Ask about security risks..."
              onKeyDown={(e) => {
                if (e.key === "Enter") askAI();
              }}
              style={{
                width: "100%",

                background:
                  "linear-gradient(145deg,#0b0b0b,#141414)",

                border:
                  "1px solid rgba(255,140,66,0.12)",

                color: "white",

                padding: "12px",

                borderRadius: "12px",

                marginBottom: "12px",

                outline: "none",

                fontSize: "12px",
              }}
            />

            <button
              onClick={askAI}
              disabled={loading}
              style={{
                width: "100%",

                background:
                  "linear-gradient(135deg,#ff7a00,#ffb347)",

                border: "none",

                color: "#111",

                padding: "12px",

                borderRadius: "12px",

                cursor: "pointer",

                fontWeight: 700,

                fontSize: "12px",

                boxShadow:
                  "0 0 18px rgba(255,140,66,0.22)",
              }}
            >
              {loading
                ? "Analyzing..."
                : "Ask RepoGuardian AI"}
            </button>

          </div>

        </div>
      )}

    </>
  );
}