import { useCallback, useEffect, useRef, useState } from "react";
import {
  Home,
  ListTodo,
  Search,
  FolderGit2,
  Users2,
  Sliders,
  HandCoins,
  MessageSquare,
  BarChart3,
  Settings,
  CircleHelp,
  Bell,
  LayoutGrid,
  SunMoon,
  FlaskConical,
} from "lucide-react";
import { CaseQueuePage } from "./workspace/CaseQueuePage";
import { CaseWorkspacePage } from "./workspace/CaseWorkspacePage";
import type { Runtime, Section } from "./workspace/types";
import { request, errorText } from "./workspace/api";
import "./workspace/workspace.css";

const VALID_SECTIONS: Section[] = [
  "work",
  "customer",
  "credit",
  "case",
  "ptp",
  "interactions",
  "evidence",
  "collateral",
  "documents",
  "other",
];

function routeFromHash() {
  try {
    const parts = location.hash.slice(1).split("/");
    if (parts[1] === "cases" && parts[2]) {
      const sec = parts[3] as Section;
      return {
        id: decodeURIComponent(parts[2]),
        section: VALID_SECTIONS.includes(sec) ? sec : ("work" as Section),
      };
    }
    return { id: "", section: "work" as Section };
  } catch {
    return { id: "", section: "work" as Section };
  }
}

export function App() {
  const [route, setRoute] = useState(routeFromHash);
  const [runtime, setRuntime] = useState<Runtime | null>(null);
  const [runtimeError, setRuntimeError] = useState("");
  const [retry, setRetry] = useState(0);
  const [locked, setLocked] = useState(false);
  const [navigationError, setNavigationError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
  );

  const routeRef = useRef(route);
  const lockedRef = useRef(locked);
  routeRef.current = route;
  lockedRef.current = locked;

  const onLocked = useCallback((value: boolean) => setLocked(value), []);

  useEffect(() => {
    const abort = new AbortController();
    setRuntimeError("");
    request<Runtime>("/api/runtime", { signal: abort.signal })
      .then((r) => {
        if (!abort.signal.aborted) setRuntime(r);
      })
      .catch((e) => {
        if (!abort.signal.aborted) {
          setRuntime(null);
          setRuntimeError(errorText(e));
        }
      });
    return () => abort.abort();
  }, [retry]);

  useEffect(() => {
    const handle = () => {
      const next = routeFromHash();
      if (lockedRef.current && next.id !== routeRef.current.id) {
        history.replaceState(
          null,
          "",
          "#/cases/" +
            encodeURIComponent(routeRef.current.id) +
            "/" +
            routeRef.current.section,
        );
        setNavigationError(
          "Hoàn tất hoặc đóng biểu mẫu/cuộc gọi trước khi đổi hồ sơ.",
        );
        return;
      }
      setRoute(next);
    };
    const beforeUnload = (e: BeforeUnloadEvent) => {
      if (lockedRef.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("hashchange", handle);
    window.addEventListener("beforeunload", beforeUnload);
    return () => {
      window.removeEventListener("hashchange", handle);
      window.removeEventListener("beforeunload", beforeUnload);
    };
  }, []);

  const navigate = (id: string, section: Section = "work") => {
    if (locked && id !== route.id) {
      setNavigationError(
        "Hoàn tất hoặc đóng biểu mẫu/cuộc gọi trước khi đổi hồ sơ.",
      );
      return;
    }
    setNavigationError("");
    location.hash = id
      ? "/cases/" + encodeURIComponent(id) + "/" + section
      : "/cases";
  };

  const navMenuItems = [
    { key: "home", title: "Trang chủ", Icon: Home, targetId: "" },
    {
      key: "queue",
      title: "Danh sách công việc",
      Icon: ListTodo,
      badge: 12,
      targetId: "",
    },
    { key: "search", title: "Tìm kiếm khách hàng", Icon: Search, targetId: "" },
    { key: "cases", title: "Quản lý case", Icon: FolderGit2, targetId: "" },
    {
      key: "debtor360",
      title: "Debtor 360",
      Icon: Users2,
      targetId: route.id || "CURRENT",
      highlight: true,
    },
    { key: "strategy", title: "Chiến lược & xử lý", Icon: Sliders, targetId: "" },
    { key: "ptp_nav", title: "PTP & Thanh toán", Icon: HandCoins, targetId: "" },
    { key: "history", title: "Trao đổi & lịch sử", Icon: MessageSquare, targetId: "" },
    { key: "reports", title: "Báo cáo", Icon: BarChart3, targetId: "" },
    { key: "settings", title: "Cấu hình", Icon: Settings, targetId: "" },
  ];

  return (
    <div id="bc-workspace" style={{ colorScheme: theme }}>
      {/* Top Global Header */}
      <header className="bc-global-header">
        <div className="bc-header-brand">
          <div className="bc-bidv-logo-wrap">
            <span className="bc-bidv-name">BIDV</span>
            <span className="bc-bidv-flower" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="#F2A900">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2C13 4.5 13 7 12 9.5C11 7 11 4.5 12 2Z" />
                <path d="M12 14.5C13 17 13 19.5 12 22C11 19.5 11 17 12 14.5Z" />
                <path d="M2 12C4.5 11 7 11 9.5 12C7 13 4.5 13 2 12Z" />
                <path d="M14.5 12C17 11 19.5 11 22 12C19.5 13 17 13 14.5 12Z" />
              </svg>
            </span>
          </div>
          <span className="bc-bidv-slogan">
            Vững bước tiên phong · Đồng hành Phát triển
          </span>
        </div>

        {/* Global Search Omnibox */}
        <div className="bc-header-search">
          <Search size={16} className="bc-search-icon" />
          <input
            type="text"
            placeholder="Tìm khách hàng, số CMND/CCCD, mã khoản vay, mã case..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <kbd className="bc-kbd">⌘ K</kbd>
        </div>

        {/* Header Right Actions */}
        <div className="bc-header-actions">
          <button
            type="button"
            className="bc-header-btn"
            aria-label="Thông báo"
            title="3 thông báo mới"
          >
            <Bell size={18} />
            <span className="bc-badge-count">3</span>
          </button>

          <button
            type="button"
            className="bc-header-btn"
            aria-label="Ứng dụng hệ thống"
            title="Danh sách ứng dụng"
          >
            <LayoutGrid size={18} />
          </button>

          <button
            type="button"
            className="bc-header-btn"
            aria-label="Đổi giao diện sáng tối"
            title="Đổi giao diện"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            <SunMoon size={18} />
          </button>

          {/* User Profile */}
          <div className="bc-header-user">
            <div className="bc-user-avatar">
              <span>NL</span>
            </div>
            <div className="bc-user-info">
              <strong className="bc-user-name">Nguyễn Thị Lan</strong>
              <small className="bc-user-dept">Phòng Thu hồi nợ</small>
            </div>
          </div>
        </div>
      </header>

      <div className="bc-main-layout">
        {/* Left Sidebar */}
        <aside className="bc-sidebar" aria-label="Điều hướng hệ thống">
          <nav className="bc-nav" aria-label="Menu chức năng">
            {navMenuItems.map((item) => {
              const isActive =
                item.key === "debtor360"
                  ? !!route.id
                  : item.key === "queue"
                  ? !route.id
                  : false;

              return (
                <button
                  key={item.key}
                  type="button"
                  className={`bc-nav-item ${isActive ? "active" : ""} ${
                    item.highlight ? "highlight" : ""
                  }`}
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => {
                    if (item.key === "queue") {
                      navigate("");
                    } else if (item.key === "debtor360") {
                      if (route.id) navigate(route.id, route.section);
                    }
                  }}
                >
                  <item.Icon size={18} className="bc-nav-icon" />
                  <span className="bc-nav-text">{item.title}</span>
                  {item.badge && (
                    <span className="bc-nav-badge">{item.badge}</span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="bc-sidebar-bottom">
            <button type="button" className="bc-nav-item bc-help-btn">
              <CircleHelp size={18} className="bc-nav-icon" />
              <span>Trợ giúp</span>
            </button>

            {/* BIDV Corporate Identity Card */}
            <div className="bc-corp-card">
              <div className="bc-corp-flower" aria-hidden="true">
                ✻
              </div>
              <p className="bc-corp-text">
                Vì một
                <br />
                <strong>Việt Nam</strong>
                <br />
                thịnh vượng
              </p>
            </div>
          </div>
        </aside>

        {/* Content Body */}
        <main className="bc-body">
          {/* Runtime banner notice */}
          <div className="bc-demo" role="status">
            <FlaskConical aria-hidden="true" size={16} />
            <span>
              {runtime
                ? runtime.simulation
                  ? runtime.mode.toUpperCase() +
                    " · Dữ liệu mô phỏng, không thực hiện cuộc gọi thật"
                  : "INTEGRATION · Chỉ đọc; AI mô phỏng và tác nghiệp bị vô hiệu hóa"
                : "Chưa xác định runtime · Tạm khóa toàn bộ tác nghiệp"}
            </span>
            {runtimeError && (
              <button className="bc-link" onClick={() => setRetry(retry + 1)}>
                Thử lại runtime
              </button>
            )}
          </div>

          {navigationError && (
            <p className="bc-error" role="alert">
              {navigationError}
            </p>
          )}

          {route.id ? (
            <CaseWorkspacePage
              key={route.id}
              caseId={route.id}
              section={route.section}
              setSection={(s) => navigate(route.id, s)}
              runtime={runtime}
              onLocked={onLocked}
            />
          ) : (
            <CaseQueuePage onSelect={(id) => navigate(id)} />
          )}
        </main>
      </div>
    </div>
  );
}
