import { useEffect, useRef } from "react";
import Shell from "./components/Shell";
import { useHashRoute, useHealth } from "./hooks";
import About from "./pages/About";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import NewCase from "./pages/NewCase";
import Queue from "./pages/Queue";

export default function App() {
  const [route, arg] = useHashRoute();
  const health = useHealth();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    document.getElementById("main")?.focus();
    window.scrollTo(0, 0);
  }, [route, arg]);

  let page;
  switch (route) {
    case "new": page = <NewCase health={health.info} />; break;
    case "cases": page = <Cases id={arg} key={arg || "list"} />; break;
    case "queue": page = <Queue />; break;
    case "about": page = <About />; break;
    default: page = <Dashboard key={health.state === "online" ? "on" : "off"} />;
  }
  const active = ["dashboard", "new", "cases", "queue", "about"].includes(route) ? route : "dashboard";
  return <Shell route={active} health={health}>{page}</Shell>;
}
