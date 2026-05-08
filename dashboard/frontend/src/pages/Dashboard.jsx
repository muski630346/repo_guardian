import { useEffect, useState } from "react";
import { getAgentStatus } from "../api/client";

import HealthScoreCard from "../components/cards/HealthScoreCard";
import StatCard from "../components/cards/StatCard";

import AgentStatusPanel from "../components/AgentStatusPanel";
import TrendChart from "../components/charts/TrendChart";

import FindingsTable from "../components/tables/FindingsTable";

import Copilot from "../components/Copilot";
import ExecutiveSummary from "../components/ExecutiveSummary";
import RiskChart from "../components/charts/RiskChart";
import AutoFixPanel from "../components/AutoFixPanel";

export default function Dashboard() {

  const [data, setData] = useState(null);
  const [agents, setAgents] = useState([]);
  const [activity, setActivity] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [toast, setToast] = useState(null);
  const [scanning, setScanning] = useState(false);

  const [executive, setExecutive] = useState(null);

  // 🔥 Fetch dashboard
  const fetchDashboard = () => {

    fetch("http://localhost:8000/api/dashboard")
      .then(r => {

        if (!r.ok)
          throw new Error(`HTTP ${r.status}`);

        return r.json();

      })
      .then(d => {

        setData(d);
        setError(null);

      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));

  };

  useEffect(() => {

    fetchDashboard();

    // 🔥 Executive summary
    fetch("http://localhost:8000/api/executive-summary")
      .then(r => r.json())
      .then(setExecutive)
      .catch(console.error);

    // 🔥 Agent polling
    const poll = () => {

      getAgentStatus()
        .then(setAgents)
        .catch(() => {});

    };

    poll();

    const id = setInterval(poll, 3000);

    // 🔥 Live activity polling
    const pollActivity = () => {

      fetch("http://localhost:8000/api/activity")
        .then(r => r.json())
        .then(setActivity)
        .catch(() => {});

    };

    pollActivity();

    const activityId = setInterval(
      pollActivity,
      2000
    );

    return () => {

      clearInterval(id);
      clearInterval(activityId);

    };

  }, []);

  // 🔥 Scan history
  const handleScanHistory = () => {

    setScanning(true);

    setToast("🧠 AI scanning repository history...");

    fetch("http://localhost:8000/api/scan-history", {
      method: "POST"
    })
      .then(r => r.json())
      .then(d => {

        setScanning(false);

        setToast(`✅ Scan complete — ${d.findings} threats detected`);

        setTimeout(() => setToast(null), 3000);

        fetchDashboard();

      })
      .catch(() => {

        setScanning(false);

        setToast("❌ Scan failed");

        setTimeout(() => setToast(null), 3000);

      });

  };

  if (loading) {
    return (
      <div style={{
        color: "#8b949e",
        padding: "40px",
        fontSize: "14px"
      }}>
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        color: "#da3633",
        padding: "40px",
        fontSize: "14px"
      }}>
        ❌ Error: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{
        color: "#8b949e",
        padding: "40px"
      }}>
        No dashboard data returned.
      </div>
    );
  }

  const S = {

    section: {
      background: "#161b22",
      border: "1px solid #21262d",
      borderRadius: "10px",
      overflow: "hidden",
    },

    sectionHeader: {
      padding: "14px 20px",
      borderBottom: "1px solid #21262d",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
    },

    sectionTitle: {
      fontSize: "13px",
      fontWeight: 600,
      color: "#e6edf3",
    },

    btn: (green = false) => ({
      background: green ? "#238636" : "#21262d",
      border: `1px solid ${green ? "#2ea043" : "#30363d"}`,
      color: "white",
      padding: "7px 14px",
      borderRadius: "8px",
      fontSize: "12px",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: "6px",
    }),

  };

  return (

    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: "18px",
      paddingBottom: "120px"
    }}>

      {/* 🔥 Toast */}
      {toast && (
        <div style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          background: "#161b22",
          border: "1px solid #30363d",
          color: "white",
          padding: "12px 16px",
          borderRadius: "10px",
          zIndex: 9999,
          boxShadow: "0 0 20px rgba(0,0,0,0.4)"
        }}>
          {toast}
        </div>
      )}

      {/* 🔥 Executive Summary */}
      {executive && (
        <ExecutiveSummary data={executive} />
      )}

      {/* 🔥 Top Stats */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1.2fr 1fr 1fr 1fr",
        gap: "12px"
      }}>

        <HealthScoreCard score={data.health_score ?? 0} />

        <StatCard
          title="Open Findings"
          value={data.open_findings ?? 0}
        />

        <StatCard
          title="PRs Reviewed"
          value={data.pr_count ?? 0}
        />

        <StatCard
          title="Active Agents"
          value={data.active_agents ?? 0}
          unit="/ 4"
        />

      </div>

      {/* 🔥 Agent Status */}
      <div style={S.section}>

        <div style={S.sectionHeader}>

          <span style={S.sectionTitle}>
            Agent Status
          </span>

          <span style={{
            fontSize: "11px",
            color: "#484f58"
          }}>
            live • polls every 3s
          </span>

        </div>

        <div style={{
          padding: "16px 20px"
        }}>
          <AgentStatusPanel agents={agents} />
        </div>

      </div>

      {/* 🔥 Analytics */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "12px"
      }}>

        <div style={S.section}>

          <div style={S.sectionHeader}>

            <span style={S.sectionTitle}>
              Security Trend
            </span>

          </div>

          <div style={{
            padding: "16px 8px 8px 8px"
          }}>
            <TrendChart data={data.score_history || []} />
          </div>

        </div>

        <div style={S.section}>

          <div style={S.sectionHeader}>

            <span style={S.sectionTitle}>
              Risk Distribution Analytics
            </span>

          </div>

          <div style={{
            padding: "20px"
          }}>
            <RiskChart findings={data.findings || []} />
          </div>

        </div>

      </div>

      {/* 🔥 Findings */}
      <div style={S.section}>

        <div style={S.sectionHeader}>

          <span style={S.sectionTitle}>
            Active Threat Intelligence
          </span>

        </div>

        <div style={{
          padding: "16px 20px"
        }}>

          <FindingsTable findings={data.findings || []} />

        </div>

      </div>

      {/* 🔥 AI Remediation */}
      <div style={S.section}>

        <div style={S.sectionHeader}>

          <span style={S.sectionTitle}>
            AI Remediation Engine
          </span>

        </div>

        <div style={{
          padding: "20px"
        }}>

          <AutoFixPanel />

        </div>

      </div>

      {/* 🔥 Compliance */}
      <div style={S.section}>

        <div style={S.sectionHeader}>

          <span style={S.sectionTitle}>
            Compliance & Governance
          </span>

        </div>

        <div style={{
          padding: "16px 20px",
          display: "flex",
          gap: "10px",
          flexWrap: "wrap"
        }}>

          <button
            style={S.btn(true)}
            onClick={() =>
              window.open("http://localhost:8000/api/export-report")
            }
          >
            📋 Export Security Report
          </button>

          <button
            style={S.btn()}
            onClick={() =>
              window.open("http://localhost:8000/api/compliance/sbom")
            }
          >
            📦 SBOM Export
          </button>

          <button
            style={S.btn()}
            onClick={handleScanHistory}
            disabled={scanning}
          >
            {scanning
              ? "🧠 AI scanning repository..."
              : "🔍 Scan Git History"}
          </button>

        </div>

      </div>

      {/* 🔥 Live Activity */}
      <div style={S.section}>

        <div style={S.sectionHeader}>

          <span style={S.sectionTitle}>
            Live Security Activity
          </span>

        </div>

        <div style={{
          padding: "18px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "12px"
        }}>

          {activity.map((item, idx) => (

            <div
              key={idx}
              style={{
                background: "#0d1117",
                border: "1px solid #21262d",
                padding: "14px",
                borderRadius: "10px",
                color: "#c9d1d9",
                fontSize: "13px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}
            >

              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}>

                <span style={{
                  fontSize: "18px"
                }}>
                  {
                    item.level === "critical"
                      ? "🚨"
                      : item.level === "success"
                      ? "✅"
                      : "📡"
                  }
                </span>

                <span>
                  {item.message}
                </span>

              </div>

              <span style={{
                color: "#8b949e",
                fontSize: "11px"
              }}>
                {item.time}
              </span>

            </div>

          ))}

        </div>

      </div>

      <Copilot />

    </div>
  );
}