import { BrowserRouter as Router, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { Settings } from "lucide-react";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import EditorTestPage from "./components/EditorTestPage";
import EditorPage from "./components/EditorPage";
import SettingsPage from "./components/SettingsPage";
import LinkProcess from "./components/LinkProcess";
import LibraryPage from "./components/LibraryPage";
import LibraryArticlePage from "./components/LibraryArticlePage";

// 全局文档库入口：设置页左侧的悬浮按钮，随时进入检索
function LibraryButton() {
  const location = useLocation();
  const navigate = useNavigate();
  if (location.pathname === "/library") return null;
  return (
    <button
      onClick={() => navigate("/library")}
      title="个人文档库（跨任务检索所有已生成内容）"
      className="fixed bottom-6 right-20 z-[100] w-12 h-12 rounded-full bg-white/90 backdrop-blur border border-gray-200 shadow-lg flex items-center justify-center text-gray-500 hover:text-primary-600 hover:border-primary-300 hover:shadow-xl hover:scale-105 transition"
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    </button>
  );
}

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
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/library/article/:docId/:scope" element={<LibraryArticlePage />} />
        <Route path="/editor/:taskId" element={<EditorPage />} />
        <Route path="/editor-test" element={<EditorTestPage />} />
      </Routes>
      <LibraryButton />
      <GlobalSettingsButton />
    </Router>
  );
}

export default App;
