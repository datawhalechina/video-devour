export const PROVIDER_PRESETS = {
  llm: [
    {
      key: "dashscope",
      label: "DashScope 阿里云",
      url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      models: ["qwen-max", "qwen-plus", "qwen-turbo"],
    },
    {
      key: "stepfun",
      label: "阶跃星辰 StepFun",
      url: "https://api.stepfun.com/step_plan/v1",
      models: ["step-3.7-flash", "step-3.5-flash"],
    },
    {
      key: "deepseek",
      label: "DeepSeek",
      url: "https://api.deepseek.com/v1",
      models: ["deepseek-chat", "deepseek-reasoner"],
    },
    {
      key: "ark",
      label: "火山方舟",
      url: "https://ark.cn-beijing.volces.com/api/v3",
      models: ["doubao-seed-1-6-flash-250828"],
    },
    {
      key: "openai",
      label: "OpenAI",
      url: "https://api.openai.com/v1",
      models: ["gpt-4o", "gpt-4o-mini"],
    },
  ],
  vlm: [
    {
      key: "dashscope",
      label: "DashScope 阿里云",
      url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      models: ["qwen-vl-max", "qwen-vl-plus"],
    },
    {
      key: "stepfun",
      label: "阶跃星辰 StepFun",
      url: "https://api.stepfun.com/step_plan/v1",
      models: ["step-3.7-flash"],
    },
    {
      key: "ark",
      label: "火山方舟",
      url: "https://ark.cn-beijing.volces.com/api/v3",
      models: ["doubao-seed-1-6-flash-250828"],
    },
    {
      key: "openai",
      label: "OpenAI",
      url: "https://api.openai.com/v1",
      models: ["gpt-4o"],
    },
  ],
};
