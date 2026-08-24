import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Moon, Sun, ShieldCheck } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { useAuth } from "../../context/AuthContext";
import { ADMIN_PATH } from "../../constants/adminPath";

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language.startsWith("fr") ? "en" : "fr");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-black/5 dark:border-white/10 bg-white/70 dark:bg-neutral-900/70 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo/logo-full.png" alt="GTCam" className="h-10 w-10 rounded-xl" />
          <span className="text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
            Globe<span style={{ color: "#C9975C" }}>Trotter</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          <Link to="/explore">{t("nav.search")}</Link>
          <Link to="/recommendations">{t("nav.recommendations")}</Link>
          <Link to="/itineraries">{t("nav.itineraries")}</Link>
          <Link to="/how-to-use">{t("nav.howToUse")}</Link>
          {isAuthenticated && <Link to="/my-places">{t("nav.myPlaces")}</Link>}
          {/* Only rendered for admins — purely a convenience shortcut once
              you're already authenticated. The hidden ADMIN_PATH URL still
              works too (e.g. before you're sure you're logged in), and the
              real access control lives server-side regardless of which
              way someone arrives at the page. */}
          {user?.is_admin && (
            <Link to={ADMIN_PATH} className="inline-flex items-center gap-1">
              <ShieldCheck size={15} />
              {t("nav.adminDashboard")}
            </Link>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleLanguage}
            className="rounded-full px-3 py-1 text-xs font-semibold border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            aria-label="Toggle language"
          >
            {i18n.language.startsWith("fr") ? "FR" : "EN"}
          </button>

          <button
            onClick={toggleTheme}
            className="rounded-full p-2 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            aria-label="Toggle dark mode"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {loading ? null : isAuthenticated ? (
            <div className="flex items-center gap-3">
              <Link
                to="/profile"
                className="text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:underline"
              >
                {user?.username}
              </Link>
              <button
                onClick={handleLogout}
                className="rounded-full border border-neutral-300 dark:border-neutral-600 px-4 py-1.5 text-sm font-semibold text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
              >
                {t("nav.logout")}
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="rounded-full bg-teal-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-teal-800 transition"
            >
              {t("nav.login")}
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
