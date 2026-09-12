/**
 * 桌面壳（pywebview）原生桥的薄封装。
 *
 * 仅桌面客户端内可用：window.pywebview.api 由 pywebview 注入，
 * 浏览器（开发模式 / 纯 Web 部署）下不存在，需降级为提示。
 */

/** 是否运行在桌面客户端内 */
export const isDesktopClient = () =>
  typeof window !== 'undefined' && !!(window.pywebview && window.pywebview.api);

/**
 * 应用内登录读取：桌面壳打开内嵌浏览器窗口，用户登录后由 WebView2 读取登录态。
 * @param {'bilibili'|'youtube'|'yuanbao'|'douyin'} platform
 * @returns {Promise<{ok:boolean,label?:string,field?:string,count?:number,error?:string,attempts?:string[]}>}
 */
export const captureLogin = (platform) => {
  const api = typeof window !== 'undefined' ? window.pywebview?.api : null;
  if (!api || typeof api.capture_login !== 'function') {
    return Promise.reject(
      new Error('当前不在桌面客户端中，无法使用应用内登录读取；请手动粘贴 Cookie')
    );
  }
  return api.capture_login(platform);
};
