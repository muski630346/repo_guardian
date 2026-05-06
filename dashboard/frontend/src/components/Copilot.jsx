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
          width: "54px",
          height: "54px",
          borderRadius: "50%",
          border: "1px solid #30363d",
          background: "#161b22",
          color: "#58a6ff",
          fontSize: "22px",
          cursor: "pointer",
          zIndex: 1000,
          boxShadow: "0 0 20px rgba(0,0,0,0.45)"
        }}
      >
        🤖
      </button>

      {/* AI Panel */}
      {open && (

        <div style={{
          position: "fixed",
          bottom: "82px",
          right: "18px",
          width: "320px",
          height: "430px",
          background: "#0d1117ee",
          border: "1px solid #30363d",
          borderRadius: "16px",
          overflow: "hidden",
          zIndex: 1000,
          boxShadow: "0 0 40px rgba(0,0,0,0.5)",
          display: "flex",
          flexDirection: "column",
          animation: "slideUp 0.2s ease-out",
          backdropFilter: "blur(10px)"
        }}>

          {/* Header */}
          <div style={{
            padding: "12px 14px",
            borderBottom: "1px solid #21262d",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "#111827"
          }}>

            <div>
              <div style={{
                color: "#58a6ff",
                fontWeight: 700,
                fontSize: "14px"
              }}>
                🤖 RepoGuardian AI
              </div>

              <div style={{
                color: "#8b949e",
                fontSize: "10px",
                marginTop: "2px"
              }}>
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
                fontSize: "16px"
              }}
            >
              ✕
            </button>

          </div>

          {/* Messages */}
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "14px",
            display: "flex",
            flexDirection: "column",
            gap: "10px"
          }}>

            {messages.length === 0 && (
              <div style={{
                color: "#8b949e",
                fontSize: "12px",
                lineHeight: "1.8"
              }}>
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

                  <div style={{
                    background: "#1f6feb",
                    color: "white",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    maxWidth: "85%",
                    marginLeft: "auto",
                    fontSize: "12px",
                    lineHeight: "1.6"
                  }}>
                    {m.text}
                  </div>

                ) : (

                  <div style={{
                    background: "#161b22",
                    border: "1px solid #21262d",
                    color: "#c9d1d9",
                    padding: "12px",
                    borderRadius: "12px",
                    fontSize: "12px",
                    lineHeight: "1.7",
                    whiteSpace: "pre-line"
                  }}>
                    {m.text}
                  </div>

                )}

              </div>

            ))}

            {loading && (
              <div style={{
                background: "#161b22",
                border: "1px solid #21262d",
                color: "#8b949e",
                padding: "10px 12px",
                borderRadius: "10px",
                fontSize: "12px"
              }}>
                RepoGuardian AI analyzing threat posture...
              </div>
            )}

          </div>

          {/* Suggestions */}
          <div style={{
            padding: "0 12px 8px 12px",
            display: "flex",
            flexWrap: "wrap",
            gap: "6px"
          }}>

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
                  background: "#161b22",
                  border: "1px solid #30363d",
                  color: "#8b949e",
                  padding: "5px 8px",
                  borderRadius: "20px",
                  fontSize: "10px",
                  cursor: "pointer"
                }}
              >
                {item}
              </button>

            ))}

          </div>

          {/* Input */}
          <div style={{
            padding: "12px",
            borderTop: "1px solid #21262d"
          }}>

            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about security risks..."
              onKeyDown={(e) => {
                if (e.key === "Enter") askAI();
              }}
              style={{
                width: "100%",
                background: "#161b22",
                border: "1px solid #30363d",
                color: "white",
                padding: "10px",
                borderRadius: "8px",
                marginBottom: "10px",
                outline: "none",
                fontSize: "12px"
              }}
            />

            <button
              onClick={askAI}
              disabled={loading}
              style={{
                width: "100%",
                background: "#238636",
                border: "none",
                color: "white",
                padding: "10px",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: "12px"
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