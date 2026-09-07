import { useCallback, useEffect, useRef, useState } from "react";
import {
  BriefcaseBusiness,
  ListTodo,
  Handshake,
  Radar,
  FlaskConical,
  SunMoon,
} from "lucide-react";
import { CaseQueuePage } from "./workspace/CaseQueuePage";
import { CaseWorkspacePage } from "./workspace/CaseWorkspacePage";
import type { Runtime, Section } from "./workspace/types";
import { request, errorText } from "./workspace/api";
import "./workspace/workspace.css";

function routeFromHash() {
  try {
    const parts = location.hash.slice(1).split("/");
    return parts[1] === "cases" && parts[2]
      ? {
          id: decodeURIComponent(parts[2]),
          section: (["work", "ptp", "evidence"].includes(parts[3])
            ? parts[3]
            : "work") as Section,
        }
      : { id: "", section: "work" as Section };
  } catch {
    return { id: "", section: "work" as Section };
  }
}
export function App() {
  const [route, setRoute] = useState(routeFromHash);
  const [runtime, setRuntime] = useState<Runtime | null>(null),
    [runtimeError, setRuntimeError] = useState(""),
    [retry, setRetry] = useState(0);
  const [locked, setLocked] = useState(false),
    [navigationError, setNavigationError] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light",
  );
  const routeRef = useRef(route),
    lockedRef = useRef(locked);
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
  const navItems = [
    { key: "queue", title: "Danh sách hồ sơ", Icon: ListTodo },
    { key: "work", title: "Hồ sơ xử lý", Icon: BriefcaseBusiness },
    { key: "ptp", title: "PTP & thanh toán", Icon: Handshake },
    { key: "evidence", title: "EWS & bằng chứng", Icon: Radar },
  ];
  return (
    <div id="bc-workspace" style={{ colorScheme: theme }}>
      <aside className="bc-sidebar">
        <div className="bc-brand">
          <div>
            <b>BIDV</b>
            <span className="bc-flower" aria-hidden="true">
              ✳
            </span>
          </div>
          <p>B.Collection</p>
          <small>COLLECTION WORKSPACE</small>
        </div>
        <nav className="bc-nav" aria-label="Điều hướng chính">
          <div className="bc-nav-label">KHÔNG GIAN LÀM VIỆC</div>
          {navItems.map(({ key, title, Icon }) => (
            <button
              key={key}
              aria-current={
                (!route.id ? key === "queue" : key === route.section)
                  ? "page"
                  : undefined
              }
              disabled={key !== "queue" && !route.id}
              onClick={() =>
                navigate(
                  key === "queue" ? "" : route.id,
                  key === "queue" ? "work" : (key as Section),
                )
              }
            >
              <Icon aria-hidden="true" />
              {title}
            </button>
          ))}
        </nav>
        <div className="bc-sidebar-foot">
          B.Collection POC
          <br />
          <small>Chưa dùng vận hành thực tế</small>
        </div>
      </aside>
      <div className="bc-body">
        <header className="bc-topbar">
          <span>
            Hồ sơ xử lý / <strong>{route.id || "Danh sách"}</strong>
          </span>
          <button
            className="bc-link"
            aria-label="Đổi giao diện sáng tối"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            <SunMoon />
            {theme === "light" ? "Sáng" : "Tối"}
          </button>
        </header>
        <div className="bc-demo" role="status">
          <FlaskConical aria-hidden="true" />
          {runtime
            ? runtime.simulation
              ? runtime.mode.toUpperCase() +
                " · Dữ liệu mô phỏng, không thực hiện cuộc gọi thật"
              : "INTEGRATION · Chỉ đọc; AI mô phỏng và tác nghiệp bị vô hiệu hóa"
            : "Chưa xác định runtime · Tạm khóa toàn bộ tác nghiệp"}
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
      </div>
    </div>
  );
}
