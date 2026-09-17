import LearningPage from './features/learning/LearningPage'
import AntTheme from './theme/AntTheme';
import { ThemeProvider } from './theme/ThemeProvider';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import AppShell from "./components/AppShell";
import ConfigGateProvider from "./components/ConfigGateProvider";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import { lazy, Suspense } from "react";
const EditorPage = lazy(() => import("./features/editor/ReportEditorPage"));
import SettingsPage from "./components/SettingsPage";
import LinkProcess from "./components/LinkProcess";
import LibraryPage from "./components/LibraryPage";
import LibraryArticlePage from "./components/LibraryArticlePage";
import LibraryVideoPage from "./components/LibraryVideoPage";

function App() {
  return (
    <ThemeProvider><AntTheme><Router>
      <MotionConfig reducedMotion="user"><ConfigGateProvider><AppShell><Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/link" element={<LinkProcess />} />
        <Route path="/upload" element={<MainApp />} />
        <Route path="/processing" element={<MainApp initialView="processing" />} />
        <Route path="/processing/:taskId" element={<MainApp initialView="processing" />} />
        <Route path="/report" element={<MainApp initialView="report" />} />
        <Route path="/report/:taskId" element={<MainApp initialView="report" />} />
        <Route path="/learn/:taskId/:kind" element={<LearningPage />} />
        <Route path="/history" element={<MainApp initialView="history" />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/library/video/:videoKey" element={<LibraryVideoPage />} />
        <Route path="/library/article/:docId/:scope" element={<LibraryArticlePage />} />
        <Route path="/editor/:taskId" element={<Suspense fallback={<div role="status">正在打开编辑器…</div>}><EditorPage /></Suspense>} />
      </Routes>
      </AppShell></ConfigGateProvider></MotionConfig>
    </Router></AntTheme></ThemeProvider>
  );
}

export default App;
