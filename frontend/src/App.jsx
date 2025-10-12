import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import EditorTestPage from "./components/EditorTestPage";
import EditorPage from "./components/EditorPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<MainApp />} />
        <Route path="/processing" element={<MainApp initialView="processing" />} />
        <Route path="/processing/:taskId" element={<MainApp initialView="processing" />} />
        <Route path="/report" element={<MainApp initialView="report" />} />
        <Route path="/report/:taskId" element={<MainApp initialView="report" />} />
        <Route path="/history" element={<MainApp initialView="history" />} />
        <Route path="/editor/:taskId" element={<EditorPage />} />
        <Route path="/editor-test" element={<EditorTestPage />} />
      </Routes>
    </Router>
  );
}

export default App;
