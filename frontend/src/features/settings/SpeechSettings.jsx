import { motion } from "framer-motion";
import { Input } from "antd";
import { TestResult } from "./ModelControls";
import { inputClass } from "./fieldStyles";
import { labelClass } from "./fieldStyles";
import { Radio, HardDriveDownload, KeyRound, Loader2 } from "lucide-react";

export default function SpeechSettings({ model, activeSection }) {
  const {
    form,
    testing,
    testResults,
    offlineCheck,
    setField,
    handleTest,
    checkOffline,
  } = model;
  return (
    <>
      {/* ASR 模式 */}
      <motion.section
        hidden={activeSection !== "asr"}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
      >
        <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center space-x-2">
          <Radio className="w-5 h-5 text-primary-600" />
          <span>语音识别模式</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => setField("asr_mode", "offline")}
            className={`p-4 rounded-xl border-2 text-left transition ${form.asr_mode === "offline" ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}
          >
            <div className="flex items-center space-x-2 mb-1">
              <HardDriveDownload className="w-5 h-5 text-gray-700" />
              <span className="font-semibold text-gray-900">
                离线模式（本地模型）
              </span>
            </div>
            <p className="text-sm text-gray-500">
              本地 FunASR Paraformer，无 API 消耗；需下载约 2GB
              模型，首次很慢且占资源（按需安装）
            </p>
          </button>
          <button
            onClick={() => setField("asr_mode", "online")}
            className={`p-4 rounded-xl border-2 text-left transition ${form.asr_mode === "online" ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}
          >
            <div className="flex items-center space-x-2 mb-1">
              <Radio className="w-5 h-5 text-gray-700" />
              <span className="font-semibold text-gray-900">
                在线模式（云端 API）
              </span>
            </div>
            <p className="text-sm text-gray-500">
              云端识别，零模型下载、启动即用（推荐），需填写 API Key
            </p>
          </button>
        </div>

        {form.asr_mode === "online" && (
          <div className="mt-5 space-y-4">
            <div>
              <label className={labelClass}>云端识别提供商</label>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={() => {
                    setField("online_asr_provider", "dashscope");
                    setField("online_asr_model", "fun-asr-realtime");
                  }}
                  className={`px-5 py-2 rounded-lg border-2 text-sm font-medium transition ${form.online_asr_provider === "dashscope" ? "border-primary-500 bg-primary-50 text-primary-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}
                >
                  DashScope（阿里云）
                </button>
                <button
                  onClick={() => {
                    setField("online_asr_provider", "stepfun");
                    setField("online_asr_model", "stepaudio-2.5-asr");
                  }}
                  className={`px-5 py-2 rounded-lg border-2 text-sm font-medium transition ${form.online_asr_provider === "stepfun" ? "border-primary-500 bg-primary-50 text-primary-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}
                >
                  阶跃星辰 StepFun
                </button>
              </div>
            </div>
            {form.online_asr_provider === "stepfun" ? (
              <div>
                <label htmlFor="setting-stepfun_api_key" className={labelClass}>
                  StepFun API Key
                </label>
                <Input.Password
                  id="setting-stepfun_api_key"
                  value={form.stepfun_api_key || ""}
                  onChange={(e) => setField("stepfun_api_key", e.target.value)}
                  placeholder="阶跃星辰 API Key"
                  className={inputClass}
                />
              </div>
            ) : (
              <div>
                <label
                  htmlFor="setting-dashscope_api_key"
                  className={labelClass}
                >
                  DashScope API Key
                </label>
                <Input.Password
                  id="setting-dashscope_api_key"
                  value={form.dashscope_api_key || ""}
                  onChange={(e) =>
                    setField("dashscope_api_key", e.target.value)
                  }
                  placeholder="sk-..."
                  className={inputClass}
                />
              </div>
            )}
            <div>
              <label htmlFor="setting-online_asr_model" className={labelClass}>
                在线识别模型
              </label>
              <Input
                id="setting-online_asr_model"
                type="text"
                value={form.online_asr_model || ""}
                onChange={(e) => setField("online_asr_model", e.target.value)}
                placeholder={
                  form.online_asr_provider === "stepfun"
                    ? "stepaudio-2.5-asr"
                    : "fun-asr-realtime"
                }
                className={inputClass}
              />
            </div>
            <button
              onClick={() => handleTest("asr")}
              disabled={testing.asr}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              {testing.asr ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <KeyRound className="w-4 h-4" />
              )}
              <span>测试在线 ASR 连通性</span>
            </button>
            <TestResult results={testResults} target="asr" />
          </div>
        )}

        {form.asr_mode === "offline" && (
          <div className="mt-5 p-4 rounded-xl bg-amber-50 border border-amber-200">
            <p className="text-sm font-semibold text-amber-800 mb-2">
              离线模式需要先安装本地模型
            </p>
            <p className="text-xs text-amber-700 leading-relaxed mb-3">
              本地语音识别约需 2GB 模型 + torch/funasr
              依赖，首次安装耗时较久且占磁盘/内存。
              若只是临时使用，建议切回「在线模式」（零下载）。
            </p>
            {offlineCheck ? (
              <div className="text-xs space-y-1 mb-3">
                <p
                  className={
                    offlineCheck.ready ? "text-green-700" : "text-amber-800"
                  }
                >
                  {offlineCheck.ready ? "✓ 环境就绪，可直接使用" : "✗ 尚未就绪"}
                </p>
                <p className="text-amber-700">
                  计算后端：{offlineCheck.compute_backend?.toUpperCase()}
                </p>
                {offlineCheck.missing_models?.length > 0 && (
                  <p className="text-amber-700">
                    缺少模型：{offlineCheck.missing_models.length} 个
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-amber-600 mb-3">正在检查环境…</p>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={checkOffline}
                className="px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-xs font-medium text-amber-800 hover:bg-amber-100"
              >
                重新检查
              </button>
              {offlineCheck && !offlineCheck.ready && (
                <span className="px-3 py-1.5 rounded-lg bg-amber-100 text-xs font-mono text-amber-800 select-all">
                  bash scripts/install_offline_asr.sh
                </span>
              )}
            </div>
          </div>
        )}
      </motion.section>
    </>
  );
}
