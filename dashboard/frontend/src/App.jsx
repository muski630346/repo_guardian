import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";

import Dashboard from "./pages/Dashboard";
import PRFeed from "./pages/PRFeed";
import Findings from "./pages/Findings";
import Developers from "./pages/Developers";



export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/prs" element={<PRFeed />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/developers" element={<Developers />} />
        </Routes>

      </Layout>
    </BrowserRouter>
  );
}