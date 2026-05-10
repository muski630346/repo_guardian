import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function VoiceCopilot() {

  const navigate = useNavigate();

  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState(
    "RepoGuardian AI Voice Copilot Ready"
  );

  const speak = (text) => {

    speechSynthesis.cancel();

    const utterance =
      new SpeechSynthesisUtterance(text);

    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    speechSynthesis.speak(utterance);
  };

  const handleCommand = async (command) => {

    const text = command.toLowerCase();

    setTranscript(command);

    // 🔥 DEVELOPER INTELLIGENCE

    if (
      text.includes("developer") ||
      text.includes("behavior") ||
      text.includes("behaviour") ||
      text.includes("profile") ||
      text.includes("tell me about") ||
      text.includes("vamshi") ||
      text.includes("muski") ||
      text.includes("snigdha") ||
      text.includes("akshitha")
    ) {

      try {

        const res = await fetch(
          "http://localhost:8000/api/developer-memory"
        );

        const memory = await res.json();

        const usernames = Object.keys(memory);

        // 🔥 SMART NAME MATCHING

        const cleanedText = text.toLowerCase();

        const found = usernames.find((u) => {

          const normalized = u.toLowerCase();

          return (
            cleanedText.includes(normalized) ||
            normalized.includes(
              cleanedText
                .replace("tell me about", "")
                .trim()
            ) ||
            cleanedText.includes("vamshi") &&
              normalized.includes("vamshi") ||

            cleanedText.includes("muski") &&
              normalized.includes("muski") ||

            cleanedText.includes("snigdha") &&
              normalized.includes("snigdha") ||

            cleanedText.includes("akshitha") &&
              normalized.includes("akshitha")
          );
        });

        if (!found) {

          const msg =
            "Developer not found in behavioral memory.";

          setResponse(msg);

          speak(msg);

          return;
        }

        const dev = memory[found];

        const msg = `
Developer ${found}.

Risk level is ${dev.risk_level}.

Top recurring issue is ${dev.top_issue}.

Trust score is ${dev.trust_score}.

Repeated mistakes count is ${dev.repeated_mistakes}.

Behavior trend is ${dev.trend}.
`;

        setResponse(msg);

        speak(msg);

      } catch (err) {

        console.error(err);

        const msg =
          "Unable to access developer intelligence memory.";

        setResponse(msg);

        speak(msg);
      }

      return;
    }

    // 🔥 SCAN

    if (
      text.includes("scan")
    ) {

      const msg =
        "Scanning repository history.";

      setResponse(msg);

      speak(msg);

      return;
    }

    // 🔥 EXPORT

    if (
      text.includes("export") ||
      text.includes("report")
    ) {

      const msg =
        "Exporting security report.";

      setResponse(msg);

      speak(msg);

      window.open(
        "http://localhost:8000/api/export-report"
      );

      return;
    }

    // 🔥 FINDINGS

    if (
      text.includes("vulnerabilities") ||
      text.includes("findings")
    ) {

      navigate("/findings");

      const msg =
        "Opening findings intelligence.";

      setResponse(msg);

      speak(msg);

      return;
    }

    // 🔥 PRS

    if (
      text.includes("pull request") ||
      text.includes("create pr")
    ) {

      navigate("/prs");

      const msg =
        "Opening pull request intelligence.";

      setResponse(msg);

      speak(msg);

      return;
    }

    // 🔥 DEVELOPERS

    if (
      text.includes("developers") ||
      text.includes("developer page")
    ) {

      navigate("/developers");

      const msg =
        "Opening developer intelligence page.";

      setResponse(msg);

      speak(msg);

      return;
    }

    // 🔥 DASHBOARD

    if (
      text.includes("dashboard")
    ) {

      navigate("/");

      const msg =
        "Opening security dashboard.";

      setResponse(msg);

      speak(msg);

      return;
    }

    // 🔥 UNKNOWN

    const msg =
      "Command not recognized.";

    setResponse(msg);

    speak(msg);
  };

  const startListening = () => {

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

      alert(
        "Speech recognition not supported."
      );

      return;
    }

    const recognition =
      new SpeechRecognition();

    recognition.lang = "en-US";

    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.start();

    recognition.onstart = () => {

      setResponse(
        "Listening..."
      );
    };

    recognition.onresult = (event) => {

      const command =
        event.results[0][0].transcript;

      handleCommand(command);
    };

    recognition.onerror = () => {

      setResponse(
        "Voice recognition failed."
      );
    };
  };

  return (
    <>
      {/* PANEL */}

      <div
        style={{
          position: "fixed",
          bottom: "120px",
          right: "30px",
          width: "340px",
          background: "#050816",
          border:
            "1px solid rgba(255,140,0,0.25)",
          borderRadius: "24px",
          padding: "22px",
          zIndex: 999999,
          boxShadow:
            "0 0 40px rgba(255,120,0,0.18)",
          backdropFilter: "blur(12px)",
        }}
      >
        <h2
          style={{
            color: "#ff9d2f",
            fontSize: "24px",
            marginBottom: "18px",
            fontWeight: "800",
          }}
        >
          🔥 REPOGUARDIAN VOICE AI
        </h2>

        <div
          style={{
            color: "#9ca3af",
            fontSize: "13px",
            marginBottom: "10px",
          }}
        >
          HEARD COMMAND
        </div>

        <div
          style={{
            background: "#0b1120",
            border:
              "1px solid rgba(255,140,0,0.15)",
            borderRadius: "16px",
            padding: "16px",
            color: "#fff",
            marginBottom: "18px",
            minHeight: "24px",
          }}
        >
          {transcript ||
            "Waiting for voice command..."}
        </div>

        <div
          style={{
            color: "#ffb347",
            lineHeight: "1.7",
            fontSize: "15px",
            whiteSpace: "pre-line",
          }}
        >
          {response}
        </div>
      </div>

      {/* BUTTON */}

      <button
        onClick={startListening}
        style={{
          position: "fixed",
          right: "28px",
          bottom: "28px",
          width: "84px",
          height: "84px",
          borderRadius: "50%",
          border: "none",
          cursor: "pointer",
          background:
            "radial-gradient(circle,#ffb347,#ff6a00)",
          color: "#fff",
          fontSize: "34px",
          zIndex: 999999,
          boxShadow:
            "0 0 35px rgba(255,120,0,0.65)",
        }}
      >
        🎙
      </button>
    </>
  );
}