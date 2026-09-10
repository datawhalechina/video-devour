import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { MotionConfig } from "framer-motion";
import AppShell from "./components/AppShell";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import EditorTestPage from "./components/EditorTestPage";
import EditorPage from "./components/EditorPage";
import SettingsPage from "./components/SettingsPage";
import LinkProcess from "./components/LinkProcess";
import LibraryPage from "./components/LibraryPage";
import LibraryArticlePage from "./components/LibraryArticlePage";
import LibraryVideoPage from "./components/LibraryVideoPage";

function App() {
  return (
    <Router>
      <MotionConfig reducedMotion="user"><AppShell><Routes>
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
        <Route path="/library/video/:videoKey" element={<LibraryVideoPage />} />
        <Route path="/library/article/:docId/:scope" element={<LibraryArticlePage />} />
        <Route path="/editor/:taskId" element={<EditorPage />} />
        <Route path="/editor-test" element={<EditorTestPage />} />
      </Routes>
      </AppShell></MotionConfig>
    </Router>
  );
}

export default App;
