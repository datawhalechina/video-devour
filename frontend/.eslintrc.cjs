module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  extends: [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react/jsx-runtime",
    "plugin:react-hooks/recommended",
  ],
  parserOptions: { ecmaVersion: "latest", sourceType: "module", ecmaFeatures: { jsx: true } },
  settings: { react: { version: "detect" } },
  plugins: ["react-refresh"],
  ignorePatterns: ["dist", "node_modules", "*.config.js"],
  rules: {
    // 未定义变量是硬错误：曾出现过组件里直接调用未解构的 guardConfig，
    // 打包能过、运行时才抛 ReferenceError（点击无反应/弹生成失败），必须在这里拦住。
    "no-undef": "error",
    // 历史代码存在未用变量等噪音，降级为警告，保证 lint 可用于回归检查而非长期红灯。
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    "no-useless-catch": "warn",
    "react/prop-types": "off",
    "react/display-name": "off",
    "react/no-unescaped-entities": "off",
    "react-hooks/exhaustive-deps": "warn",
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
  },
};
