import React from 'react'
import ReactDOM from 'react-dom/client'
import { useState } from "react"
import Dashboard from "./App.jsx"
import UserDashboard from "./userDashboard.jsx"

function AppRouter() {
  const [page, setPage] = useState(
    window.location.hash === "#/users" ? "users" : "main"
  );

  const navigate = (p) => {
    window.location.hash = p === "users" ? "#/users" : "#/";
    setPage(p);
  };

  window.onhashchange = () => {
    setPage(window.location.hash === "#/users" ? "users" : "main");
  };

  if (page === "users") return <UserDashboard onNavigate={navigate} />;

  return (
    <div>
      <style>{`
        .dev-profiles-btn {
          position: fixed; top: 14px; right: 320px; z-index: 200;
          background: rgba(99,102,241,0.12);
          border: 1px solid rgba(99,102,241,0.25);
          color: #818cf8; padding: 5px 14px; border-radius: 20px;
          font-size: 12px; font-weight: 500; cursor: pointer;
          font-family: 'Inter', sans-serif;
        }
        .dev-profiles-btn:hover { background: rgba(99,102,241,0.22); }
      `}</style>
      <button className="dev-profiles-btn" onClick={() => navigate("users")}>
        👥 Developer Profiles
      </button>
      <Dashboard />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>
)