import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { Settings } from "lucide-react";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import EditorTestPage from "./components/EditorTestPage";
import EditorPage from "./components/EditorPage";
import SettingsPage from "./components/SettingsPage";
import LinkProcess from "./components/LinkProcess";

// 全局悬浮设置入口：除设置页本身外，所有页面右下角常驻，方便随时进入控制台
function GlobalSettingsButton() {
  const location = useLocation();
  const navigate = useNavigate();
  if (location.pathname === "/settings") return null;
  return (
    <button
      onClick={() => navigate("/settings")}
      title="设置控制台（ASR / LLM / VLM / 学习阶段 / 视频号 Cookie）"
      className="fixed bottom-6 right-6 z-[100] w-12 h-12 rounded-full bg-white/90 backdrop-blur border border-gray-200 shadow-lg flex items-center justify-center text-gray-500 hover:text-primary-600 hover:border-primary-300 hover:shadow-xl hover:scale-105 transition"
    >
      <Settings className="w-5 h-5" />
    </button>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/link" element={<LinkProcess />} />
        <Route path="/upload" element={<MainApp />} />
        <Route path="/processing" element={<MainApp initialView="processing" />} />
        <Route path="/processing/:taskId" element={<MainApp initialView="processing" />} />
        <Route path="/report" element={<MainApp initialView="report" />} />
        <Route path="/report/:taskId" element={<MainApp initialView="report" />} />
        <Route path="/history" element={<MainApp initialView="history" />} />
        <Route path="/editor/:taskId" element={<EditorPage />} />
        <Route path="/editor-test" element={<EditorTestPage />} />
      </Routes>
      <GlobalSettingsButton />
    </Router>
  );
}

export default App;
