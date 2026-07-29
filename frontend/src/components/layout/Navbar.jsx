import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language.startsWith("fr") ? "en" : "fr");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-black/5 dark:border-white/10 bg-white/70 dark:bg-neutral-900/70 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo/logo-full.png" alt="GT — GlobeTrotter" className="h-10 w-10 rounded-xl" />
          <span className="text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
            Globe<span style={{ color: "#C9975C" }}>Trotter</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          <Link to="/explore">{t("nav.search")}</Link>
          <Link to="/recommendations">{t("nav.recommendations")}</Link>
          <Link to="/itineraries">{t("nav.itineraries")}</Link>
          <Link to="/how-to-use">{t("nav.howToUse")}</Link>
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

          <Link
            to="/login"
            className="rounded-full bg-teal-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-teal-800 transition"
          >
            {t("nav.login")}
          </Link>
        </div>
      </nav>
    </header>
  );
}
