import { Input } from "antd";
import { AutoComplete } from "antd";
import { PROVIDER_PRESETS } from "./presets";
import { ProviderChips } from "./ModelControls";
import { TestResult } from "./ModelControls";
import { labelClass } from "./fieldStyles";
import { KeyRound, Loader2 } from "lucide-react";

export default function ModelSettings({ model, activeSection }) {
  const {
    form,
    testing,
    testResults,
    setField,
    handleTest,
    detectProvider,
    applyProvider,
  } = model;
  return (
    <>
      {["llm", "vlm"].map((section) => (
        <section
          key={section}
          hidden={activeSection !== "models"}
          className="vd-model-card"
        >
          <header>
            <div>
              <h2>{section === "llm" ? "内容生成 LLM" : "画面理解 VLM"}</h2>
              <p>
                {section === "llm"
                  ? "用于视频内容的总结、改写、知识提炼与结构化输出。"
                  : "用于理解视频画面，识别场景、人物与相关信息。"}
              </p>
            </div>
            <button
              className="lake-secondary"
              disabled={testing[section]}
              onClick={() => handleTest(section)}
            >
              {testing[section] ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <KeyRound size={16} />
              )}
              测试连接
            </button>
          </header>
          <div className="vd-model-grid">
            <div>
              <label className={labelClass}>服务提供商</label>
              <ProviderChips
                section={section}
                detectProvider={detectProvider}
                applyProvider={applyProvider}
              />
            </div>
            <div>
              <label
                htmlFor={`setting-${section}_api_key`}
                className={labelClass}
              >
                API Key
              </label>
              <Input.Password
                id={`setting-${section}_api_key`}
                value={form[`${section}_api_key`] || ""}
                onChange={(e) => setField(`${section}_api_key`, e.target.value)}
                placeholder="填写 API Key"
              />
            </div>
            <div>
              <label
                htmlFor={`setting-${section}_api_url`}
                className={labelClass}
              >
                服务地址
              </label>
              <Input
                id={`setting-${section}_api_url`}
                value={form[`${section}_api_url`] || ""}
                onChange={(e) => setField(`${section}_api_url`, e.target.value)}
                placeholder="https://…"
              />
            </div>
            <div>
              <label
                htmlFor={`setting-${section}_model_type`}
                className={labelClass}
              >
                模型（可选择或输入）
              </label>
              <AutoComplete
                id={`setting-${section}_model_type`}
                className="workspace-select"
                value={form[`${section}_model_type`] || ""}
                onChange={(value) => setField(`${section}_model_type`, value)}
                options={(
                  PROVIDER_PRESETS[section].find(
                    (p) => detectProvider(section) === p.key,
                  )?.models || []
                ).map((value) => ({ value }))}
                placeholder="选择或填写模型名称"
              />
            </div>
          </div>
          <TestResult results={testResults} target={section} />
        </section>
      ))}
    </>
  );
}
