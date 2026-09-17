import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Save, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { PageHeader } from "../../shared/ui/Workspace";
import ThemePicker from "../../theme/ThemePicker";
import { useSettings } from "./useSettings";
import SpeechSettings from "./SpeechSettings";
import ModelSettings from "./ModelSettings";
import AccountSettings from "./AccountSettings";
import LearningSettings from "./LearningSettings";
import StorageSettings from "./StorageSettings";

function SettingsPage() {
  const model = useSettings();
  const { settings, saving, saveMessage, error, loadSettings, handleSave } =
    model;
  const [activeSection, setActiveSection] = useState("appearance");
  const fieldsRef = useRef(null);
  useEffect(() => {
    fieldsRef.current?.scrollTo(0, 0);
  }, [activeSection]);
  if (!settings) {
    return (
      <div className="lake-empty" role="status">
        {error ? (
          <>
            <p role="alert">{error}</p>
            <button className="lake-secondary" onClick={loadSettings}>
              重新加载
            </button>
          </>
        ) : (
          <>
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            <p>正在载入设置…</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="vd-settings vd-page">
      {/* 顶部导航 */}

      <>
        <PageHeader title="偏好设置" description="让每次整理，更适合你。" />
        <div className="vd-settings-layout">
          <div className="vd-settings-topbar">
            <nav className="vd-settings-nav" aria-label="设置分类">
              {[
                ["appearance", "外观主题"],
                ["asr", "语音识别"],
                ["models", "内容生成"],
                ["accounts", "平台账号"],
                ["learning", "学习偏好"],
                ["storage", "下载缓存"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  aria-pressed={activeSection === key}
                  onClick={() => setActiveSection(key)}
                >
                  {label}
                </button>
              ))}
              <p>
                设置仅保存在本机。
                <br />
                在线识别与内容生成会调用你配置的服务。
              </p>
            </nav>
            {/* 保存 */}
            <div
              hidden={activeSection === "appearance"}
              className="vd-settings-save"
            >
              {saveMessage && (
                <span
                  className={`text-sm flex items-center space-x-1 ${saveMessage.ok ? "text-green-600" : "text-red-600"}`}
                >
                  {saveMessage.ok ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <XCircle className="w-4 h-4" />
                  )}
                  <span>{saveMessage.text}</span>
                </span>
              )}
              {error && <span className="text-sm text-red-600">{error}</span>}
              <motion.button
                onClick={handleSave}
                disabled={saving}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center space-x-2 px-8 py-3 rounded-xl font-bold text-white bg-primary-600 hover:bg-primary-700 shadow-lg disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Save className="w-5 h-5" />
                )}
                <span>保存设置</span>
              </motion.button>
            </div>
          </div>
          <div ref={fieldsRef} className="vd-settings-fields">
            <div hidden={activeSection !== "appearance"}>
              <ThemePicker />
            </div>

            <SpeechSettings model={model} activeSection={activeSection} />
            <ModelSettings model={model} activeSection={activeSection} />
            <AccountSettings model={model} activeSection={activeSection} />
            <LearningSettings model={model} activeSection={activeSection} />
            <StorageSettings model={model} activeSection={activeSection} />
          </div>
        </div>
      </>
    </div>
  );
}

export default SettingsPage;
