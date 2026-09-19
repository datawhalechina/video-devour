import { CheckCircle, XCircle } from "lucide-react";
import { PROVIDER_PRESETS } from "./presets";
const SHORT_NAMES = {
  dashscope: "阿里云",
  stepfun: "阶跃星辰",
  deepseek: "DeepSeek",
  ark: "火山方舟",
  openai: "OpenAI",
};
export function ProviderChips({ section, detectProvider, applyProvider }) {
  const active = detectProvider(section);
  return (
    <div className="vd-provider-chips">
      {PROVIDER_PRESETS[section].map((provider) => (
        <button
          key={provider.key}
          title={provider.label}
          onClick={() => applyProvider(section, provider)}
          aria-pressed={active === provider.key}
        >
          {SHORT_NAMES[provider.key] || provider.label}
        </button>
      ))}
      <button
        aria-pressed={active === "custom"}
        onClick={() =>
          applyProvider(section, { key: "custom", url: "", models: [""] })
        }
      >
        自定义
      </button>
    </div>
  );
}

export function TestResult({ target, results }) {
  const result = results[target];
  if (!result) return null;
  return (
    <div
      className={`mt-2 flex items-start space-x-2 text-sm ${result.ok ? "text-green-700" : "text-red-700"}`}
    >
      {result.ok ? (
        <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
      ) : (
        <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
      )}
      <span>{result.message}</span>
    </div>
  );
}
