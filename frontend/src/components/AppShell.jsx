import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { Settings, House, Folder, Clock } from "lucide-react";

export default function AppShell({ children }) {
  const { pathname, state } = useLocation();
  const learningFromHistory = pathname.startsWith('/learn/') && state?.reader?.path?.startsWith('/report/');
  const contentRef = useRef(null);
  const links = [
    {
      to: "/",
      label: "工作台",
      icon: House,
      active: ["/", "/link", "/upload"].includes(pathname),
    },
    {
      to: "/library",
      label: "知识库",
      icon: Folder,
      active: /^\/(library|learn)(\/|$)/.test(pathname) && !learningFromHistory,
    },
    {
      to: "/history",
      label: "处理记录",
      icon: Clock,
      active: /^\/(history|processing|report|editor)(\/|$)/.test(pathname) || learningFromHistory,
    },
  ];
  useEffect(() => {
    contentRef.current?.scrollTo(0, 0);
  }, [pathname]);
  return (
    <div className="vd-app">
      <a className="skip-link" href="#workspace-content">
        跳转到内容
      </a>
      <div className="vd-shell">
        <header className="vd-sidebar">
          <Link className="vd-brand" to="/" aria-label="VideoDevour 工作台">
            <img src="/logo.png?v=whale-original-clean-20260916" alt="" />
            <span>VideoDevour</span>
          </Link>
          <nav className="vd-navigation" aria-label="主导航">
            {links.map(({ to, label, icon: Icon, active }) => (
              <Link key={to} to={to} aria-current={active ? "page" : undefined}>
                <Icon size={21} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <Link
            className="vd-settings-link"
            to="/settings"
            aria-label="偏好设置"
            aria-current={pathname === "/settings" ? "page" : undefined}
          >
            <Settings size={21} />
            <span>设置</span>
          </Link>
        </header>
        <div className="vd-content">
          <div
            ref={contentRef}
            id="workspace-content"
            className={`lake-content ${pathname.startsWith("/report/") ? "is-report-reader" : ""} ${pathname.startsWith("/library/video/") || pathname.startsWith("/library/article/") ? "is-reader" : ""}`}
            tabIndex={-1}
            aria-label="工作区内容"
          >
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
