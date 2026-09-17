import { useCallback, useEffect, useState } from "react";
import {
  getSettings,
  updateSettings,
  testSettings,
  importCookiesFromBrowser,
  youtubeEnvCheck,
} from "../../api/settingsService";
import { captureLogin } from "../../api/desktopBridge";
import { PROVIDER_PRESETS } from "./presets";

export function useSettings() {
  const [settings, setSettings] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);
  const [testing, setTesting] = useState({}); // { asr: bool, llm: bool, vlm: bool }
  const [testResults, setTestResults] = useState({}); // { asr: {ok, message}, ... }
  const [cookieImport, setCookieImport] = useState({
    loading: false,
    message: "",
    attempts: [],
  });
  const [loginCapture, setLoginCapture] = useState({
    loading: "",
    message: "",
    ok: false,
  });
  const [cacheInfo, setCacheInfo] = useState(null);
  const [offlineCheck, setOfflineCheck] = useState(null);
  const [error, setError] = useState(null);

  const loadCache = useCallback(async () => {
    try {
      const res = await fetch("/api/downloads/cache");
      if (res.ok) setCacheInfo(await res.json());
    } catch {
      // 缓存统计不可用不阻塞主设置表单。
    }
  }, []);

  const loadSettings = useCallback(async () => {
    setError(null);
    try {
      const data = await getSettings();
      setSettings(data);
      loadCache();
      setForm({
        asr_mode: data.asr_mode,
        dashscope_api_key: data.dashscope_api_key,
        online_asr_model: data.online_asr_model,
        online_asr_provider: data.online_asr_provider || "dashscope",
        stepfun_api_key: data.stepfun_api_key,

        llm_api_key: data.llm_api_key,
        llm_api_url: data.llm_api_url,
        llm_model_type: data.llm_model_type,
        vlm_api_key: data.vlm_api_key,
        vlm_api_url: data.vlm_api_url,
        vlm_model_type: data.vlm_model_type,
        default_education_level: data.default_education_level,

        wechat_yuanbao_cookie: data.wechat_yuanbao_cookie || "",
        wechat_resolver_url: data.wechat_resolver_url || "",
        wechat_resolver_token: data.wechat_resolver_token || "",
        youtube_cookies: data.youtube_cookies || "",
        douyin_cookies: data.douyin_cookies || "",
        bilibili_sessdata: data.bilibili_sessdata || "",
        cookie_browser: data.cookie_browser || "",
      });
    } catch (err) {
      setError(`加载设置失败: ${err.message}`);
    }
  }, [loadCache]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (key === "asr_mode" && value === "offline") checkOffline();
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    setError(null);
    try {
      const result = await updateSettings(form);
      setSettings(result.settings);
      setForm((prev) => ({
        ...prev,
        ...result.settings,
      }));
      setSaveMessage({ ok: true, text: "设置已保存并生效" });
    } catch (err) {
      setSaveMessage({ ok: false, text: `保存失败: ${err.message}` });
    } finally {
      setSaving(false);
    }
  };

  const [ytCheck, setYtCheck] = useState({ loading: false, result: null });

  const handleYtCheck = async () => {
    if (ytCheck.loading) return;
    setYtCheck({ loading: true, result: null });
    try {
      const result = await youtubeEnvCheck();
      setYtCheck({ loading: false, result });
    } catch (err) {
      setYtCheck({
        loading: false,
        result: { checks: {}, suggestions: [`自检失败: ${err.message}`] },
      });
    }
  };

  const checkOffline = async () => {
    try {
      const res = await fetch("/api/asr/offline-check");
      if (res.ok) setOfflineCheck(await res.json());
    } catch (e) {
      /* 忽略 */
    }
  };

  const handleImportCookies = async () => {
    if (cookieImport.loading) return;
    setCookieImport({
      loading: true,
      message:
        "正在读取浏览器 Cookie（首次可能需要 1-3 分钟；若弹出钥匙串授权请点「允许」）…",
      attempts: [],
    });
    try {
      const result = await importCookiesFromBrowser(form.cookie_browser || "");
      setCookieImport({
        loading: false,
        message: result.message,
        attempts: result.attempts || [],
      });
      // 读取到的字段由后端直接写入了设置，刷新表单中的脱敏值
      const data = await getSettings();
      setForm((prev) => ({
        ...prev,
        wechat_yuanbao_cookie:
          data.wechat_yuanbao_cookie || prev.wechat_yuanbao_cookie,
        youtube_cookies: data.youtube_cookies || prev.youtube_cookies,
        bilibili_sessdata: data.bilibili_sessdata || prev.bilibili_sessdata,
        douyin_cookies: data.douyin_cookies || prev.douyin_cookies,
      }));
    } catch (err) {
      setCookieImport({
        loading: false,
        message: `读取失败: ${err.message}`,
        attempts: [],
      });
    }
  };

  // 应用内登录读取：打开内嵌浏览器窗口登录，由桌面壳读取登录态
  const handleCaptureLogin = async (platform) => {
    if (loginCapture.loading) return;
    setLoginCapture({ loading: platform, message: "", ok: false });
    try {
      const result = await captureLogin(platform);
      if (result?.ok) {
        const data = await getSettings();
        setForm((prev) => ({
          ...prev,
          wechat_yuanbao_cookie:
            data.wechat_yuanbao_cookie || prev.wechat_yuanbao_cookie,
          youtube_cookies: data.youtube_cookies || prev.youtube_cookies,
          bilibili_sessdata: data.bilibili_sessdata || prev.bilibili_sessdata,
          douyin_cookies: data.douyin_cookies || prev.douyin_cookies,
        }));
        setLoginCapture({
          loading: "",
          ok: true,
          message: `已读取并保存 ${result.label || ""} 登录态（${result.count || 0} 个 cookie）`,
        });
      } else {
        setLoginCapture({
          loading: "",
          ok: false,
          message: result?.error || "未读取到登录态，请重试",
        });
      }
    } catch (err) {
      setLoginCapture({
        loading: "",
        ok: false,
        message: `读取失败: ${err.message}`,
      });
    }
  };

  const LOGIN_TARGETS = [
    { key: "bilibili", label: "B站" },
    { key: "youtube", label: "YouTube" },
    { key: "yuanbao", label: "腾讯元宝" },
    { key: "douyin", label: "抖音" },
  ];

  const handleTest = async (target) => {
    setTesting((prev) => ({ ...prev, [target]: true }));
    try {
      // 先保存再测试，确保测试用的是当前填写的配置
      await updateSettings(form);
      const result = await testSettings(target);
      setTestResults((prev) => ({ ...prev, ...result.results }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [target]: { ok: false, message: `测试失败: ${err.message}` },
      }));
    } finally {
      setTesting((prev) => ({ ...prev, [target]: false }));
    }
  };

  // 当前表单 URL 匹配到的供应商（未匹配则为 custom）
  const detectProvider = (section) => {
    const urlKey = section === "llm" ? "llm_api_url" : "vlm_api_url";
    const url = form[urlKey] || "";
    const hit = PROVIDER_PRESETS[section].find((p) => url.startsWith(p.url));
    return hit ? hit.key : "custom";
  };

  // 点击供应商芯片：自动填地址 + 推荐模型；StepFun 时自动复用 ASR 的 Key
  const applyProvider = (section, prov) => {
    const updates =
      section === "llm"
        ? { llm_api_url: prov.url, llm_model_type: prov.models[0] }
        : { vlm_api_url: prov.url, vlm_model_type: prov.models[0] };
    if (prov.key === "stepfun" && form.stepfun_api_key) {
      if (section === "llm" && !form.llm_api_key)
        updates.llm_api_key = form.stepfun_api_key;
      if (section === "vlm" && !form.vlm_api_key)
        updates.vlm_api_key = form.stepfun_api_key;
    }
    setForm((prev) => ({ ...prev, ...updates }));
  };

  return {
    settings,
    form,
    saving,
    saveMessage,
    testing,
    testResults,
    cookieImport,
    loginCapture,
    cacheInfo,
    offlineCheck,
    error,
    ytCheck,
    loadSettings,
    setField,
    handleSave,
    handleTest,
    handleYtCheck,
    checkOffline,
    loadCache,
    handleImportCookies,
    handleCaptureLogin,
    LOGIN_TARGETS,
    detectProvider,
    applyProvider,
  };
}
