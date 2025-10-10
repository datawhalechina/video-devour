import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Header from "./Header";
import VideoUpload from "./VideoUpload";
import ProcessingStatus from "./ProcessingStatus";
import ReportViewer from "./ReportViewer";
import HistoryList from "./HistoryList";

function MainApp({ initialView = "upload" }) {
  const [currentView, setCurrentView] = useState(initialView); // upload, processing, report, history
  const [currentTask, setCurrentTask] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);

  const handleUploadSuccess = (taskId) => {
    setCurrentTask(taskId);
    setCurrentView("processing");
  };

  const handleProcessingComplete = (report) => {
    setSelectedReport(report);
    setCurrentView("report");
  };

  const handleViewReport = (report) => {
    setSelectedReport(report);
    setCurrentView("report");
  };

  const handleBackToUpload = () => {
    setCurrentView("upload");
    setCurrentTask(null);
    setSelectedReport(null);
  };

  const handleViewHistory = () => {
    setCurrentView("history");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 flex flex-col">
      <Header
        currentView={currentView}
        onNavigate={setCurrentView}
        onBackToUpload={handleBackToUpload}
      />

      <main className="container mx-auto px-4 py-8 max-w-7xl flex-grow">
        <AnimatePresence mode="wait">
          {currentView === "upload" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <VideoUpload
                onUploadSuccess={handleUploadSuccess}
                onViewHistory={handleViewHistory}
              />
            </motion.div>
          )}

          {currentView === "processing" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ProcessingStatus
                taskId={currentTask}
                onComplete={handleProcessingComplete}
                onCancel={handleBackToUpload}
              />
            </motion.div>
          )}

          {currentView === "report" && (
            <motion.div
              key="report"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ReportViewer report={selectedReport} onBack={handleBackToUpload} />
            </motion.div>
          )}

          {currentView === "history" && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <HistoryList
                onViewReport={handleViewReport}
                onBack={handleBackToUpload}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-8 border-t border-gray-200 bg-white/50">
        <div className="text-center text-gray-600 text-sm">
          <p>🍽️ VideoDevour - 吃掉视频，输出一份报告</p>
          <p className="mt-2">基于 ASR + VLM 技术的智能视频分析工具</p>
        </div>
      </footer>
    </div>
  );
}

export default MainApp;

