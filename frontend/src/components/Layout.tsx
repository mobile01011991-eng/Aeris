import { NavLink, Outlet } from "react-router-dom";
import { useI18n } from "../i18n/I18nContext";
import { LanguageToggle } from "./LanguageToggle";

export function Layout() {
  const { t } = useI18n();

  return (
    <div className="app-shell">
      <header className="site-nav">
        <NavLink to="/" className="brand-mark">
          AE<span>RIS</span>
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
            {t("nav.analyze")}
          </NavLink>
          <NavLink
            to="/results"
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {t("nav.results")}
          </NavLink>
          <LanguageToggle />
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="footer-inner">
          <span>{t("footer.brand")}</span>
          <span>{t("footer.filters")}</span>
        </div>
      </footer>
    </div>
  );
}
