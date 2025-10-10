import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import MainApp from "./components/MainApp";
import EditorTestPage from "./components/EditorTestPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<MainApp />} />
        <Route path="/processing" element={<MainApp initialView="processing" />} />
        <Route path="/report" element={<MainApp initialView="report" />} />
        <Route path="/history" element={<MainApp initialView="history" />} />
        <Route path="/editor-test" element={<EditorTestPage />} />
      </Routes>
    </Router>
  );
}

export default App;
