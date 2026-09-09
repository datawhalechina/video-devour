import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";

import VideoUpload from "./VideoUpload";
import ProcessingStatus from "./ProcessingStatus";
import ReportViewer from "./ReportViewer";
import HistoryList from "./HistoryList";
import { getTaskReport } from "../api/videoService";

// 任务状态持久化工具函数
const STORAGE_KEY = 'videodevour_current_task';

const saveTaskToStorage = (taskId, status = 'processing', startTime = null) => {
  if (taskId) {
    const existing = loadTaskFromStorage();
    const taskData = {
      taskId,
      status,
      timestamp: Date.now(),
      startTime: startTime || existing?.startTime || Date.now()
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(taskData));
  }
};

const loadTaskFromStorage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const taskData = JSON.parse(stored);
      // 检查任务是否过期（24小时）
      const isExpired = Date.now() - taskData.timestamp > 24 * 60 * 60 * 1000;
      if (!isExpired) {
        return taskData;
      } else {
        // 清除过期任务
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  } catch (error) {
    console.error('加载任务状态失败:', error);
    localStorage.removeItem(STORAGE_KEY);
  }
  return null;
};

const clearTaskFromStorage = () => {
  localStorage.removeItem(STORAGE_KEY);
};

function MainApp({ initialView = "upload" }) {
  const { taskId: urlTaskId } = useParams();
  const navigate = useNavigate();
  const [currentView, setCurrentView] = useState(initialView);
  const [currentTask, setCurrentTask] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportError, setReportError] = useState(null);
  const [reportRetry, setReportRetry] = useState(0);

  useEffect(() => { setCurrentView(initialView) }, [initialView]);

  // 组件初始化时从localStorage恢复任务状态或使用URL参数
  useEffect(() => {
    // 优先使用URL中的taskId
    if (urlTaskId) {
      // 如果是报告页面，不设置currentTask（避免显示"正在处理"）
      if (initialView === 'report') {
        setCurrentTask(null);
      } else {
        setCurrentTask(urlTaskId);
        // 保存到localStorage
        saveTaskToStorage(urlTaskId, initialView === 'processing' ? 'processing' : 'completed');
      }
    } else {
      // 从localStorage恢复任务状态
      const storedTask = loadTaskFromStorage();
      if (storedTask && storedTask.taskId) {
        // 检查任务是否已完成，如果已完成则不显示"正在处理"
        if (storedTask.status === 'completed') {
          setCurrentTask(null);
          clearTaskFromStorage();
        } else {
          setCurrentTask(storedTask.taskId);
          // 如果有正在处理的任务且当前在上传页面，自动跳转到处理页面
          if (storedTask.status === 'processing' && initialView === 'upload') {
            setCurrentView('processing');
          }
        }
      }
    }
  }, [initialView, urlTaskId]);

  const handleUploadSuccess = (taskId) => {
    setCurrentTask(taskId);
    setCurrentView("processing");
    // 保存任务状态到localStorage
    saveTaskToStorage(taskId, 'processing');
    // 更新URL
    navigate(`/processing/${taskId}`);
  };

  const handleProcessingComplete = async (report) => {
    try {
      // 获取详细的报告数据
      const detailedReport = await getTaskReport(currentTask);
      setSelectedReport(detailedReport);
      setCurrentView("report");
      // 处理完成后清除当前任务状态
      if (currentTask) {
        // 更新URL
        navigate(`/report/${currentTask}`);
        // 清除当前任务，移除"正在处理"标签
        setCurrentTask(null);
        clearTaskFromStorage();
      }
    } catch (error) {
      console.error('获取报告详情失败:', error);
      // 如果获取详细报告失败，使用原始报告数据
      setSelectedReport(report);
      setCurrentView("report");
      if (currentTask) {
        navigate(`/report/${currentTask}`);
        // 清除当前任务，移除"正在处理"标签
        setCurrentTask(null);
        clearTaskFromStorage();
      }
    }
  };

  const handleViewReport = async (report) => {
    try {
      // 获取详细的报告数据
      const detailedReport = await getTaskReport(report.taskId || report.id);
      setSelectedReport(detailedReport);
      setCurrentView("report");
      // 如果报告有taskId，更新URL
      if (report.taskId || report.id) {
        navigate(`/report/${report.taskId || report.id}`);
      }
    } catch (error) {
      console.error('获取报告详情失败:', error);
      // 如果获取详细报告失败，使用原始报告数据
      setSelectedReport(report);
      setCurrentView("report");
      if (report.taskId || report.id) {
        navigate(`/report/${report.taskId || report.id}`);
      }
    }
  };

  // Report loads have an explicit error state and can be retried without leaving the page.
  useEffect(() => {
    if (!urlTaskId || initialView !== 'report') return;
    let cancelled = false;
    setReportError(null);
    setSelectedReport(null);
    const loadReport = async () => {
      try {
        const detailedReport = await getTaskReport(urlTaskId);
        if (!cancelled) setSelectedReport(detailedReport);
      } catch (error) {
        if (!cancelled) setReportError(error.message || '请稍后重试');
      }
    };
    loadReport();
    return () => { cancelled = true; };
  }, [urlTaskId, initialView, reportRetry]);

  const handleBackToUpload = () => {
    setCurrentView("upload");
    setCurrentTask(null);
    setSelectedReport(null);
    // 清除localStorage中的任务状态
    clearTaskFromStorage();
    // 导航到上传页面
    navigate('/upload');
  };

  const handleViewHistory = () => {
    setCurrentView("history");
    navigate('/history');
  };

  const handleBackToProcessing = () => {
    if (currentTask) {
      setCurrentView("processing");
      navigate(`/processing/${currentTask}`);
    }
  };

  // 处理任务被删除的情况
  const handleTaskDeleted = () => {
    setCurrentTask(null);
    setSelectedReport(null);
    clearTaskFromStorage();
    setCurrentView("upload");
    navigate('/upload');
  };

  // 监听currentTask变化，同步到localStorage
  useEffect(() => {
    if (currentTask) {
      const storedTask = loadTaskFromStorage();
      const currentStatus = storedTask?.status || 'processing';
      saveTaskToStorage(currentTask, currentStatus);
    }
  }, [currentTask]);

  return (
    <div className="workspace-page flex flex-col">
      <main className="container mx-auto px-4 py-8 max-w-7xl flex-grow">
        <AnimatePresence mode="wait">
          {currentView === "upload" && (
            <VideoUpload
              onUploadSuccess={handleUploadSuccess}
              onViewHistory={handleViewHistory}
              currentTask={currentTask}
              onBackToProcessing={handleBackToProcessing}
            />
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
              <ReportViewer report={selectedReport} onBack={handleViewHistory} error={reportError} onRetry={() => setReportRetry(value => value + 1)} />
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
              onBackToProcessing={handleTaskDeleted}
              currentTask={currentTask}
            />
            </motion.div>
          )}
        </AnimatePresence>
      </main>


    </div>
  );
}

export default MainApp;

