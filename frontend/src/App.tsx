import { Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-header__brand">Overturn</span>
        <span className="app-header__tagline">
          Turn every denied claim into institutional knowledge.
        </span>
        <span className="app-header__org">Riverside Medical Group</span>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
