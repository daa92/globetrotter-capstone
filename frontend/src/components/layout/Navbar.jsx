import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Moon, Sun, ShieldCheck, Menu, X, Bell } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { useAuth } from "../../context/AuthContext";
import { ADMIN_PATH } from "../../constants/adminPath";
import { unreadNotificationCount } from "../../api/client";
import UserAvatar from "./UserAvatar";

export default function Navbar() {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const { user, accessToken, isAuthenticated, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language.startsWith("fr") ? "en" : "fr");
  };

  // Poll unread count while logged in — cheap enough (one small request)
  // and simple enough not to need websockets for a capstone-scale app.
  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      setUnread(0);
      return;
    }
    let cancelled = false;
    const load = () => {
      unreadNotificationCount(accessToken)
        .then((r) => !cancelled && setUnread(r.unread_count))
        .catch(() => {});
    };
    load();
    const interval = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isAuthenticated, accessToken]);

  const navLinks = (
    <>
      <Link to="/explore" onClick={() => setMenuOpen(false)}>{t("nav.search")}</Link>
      <Link to="/recommendations" onClick={() => setMenuOpen(false)}>{t("nav.recommendations")}</Link>
      <Link to="/itineraries" onClick={() => setMenuOpen(false)}>{t("nav.itineraries")}</Link>
      <Link to="/how-to-use" onClick={() => setMenuOpen(false)}>{t("nav.howToUse")}</Link>
      {isAuthenticated && <Link to="/my-places" onClick={() => setMenuOpen(false)}>{t("nav.myPlaces")}</Link>}
      {/* Only rendered for admins — purely a convenience shortcut once
          you're already authenticated. The hidden ADMIN_PATH URL still
          works too (e.g. before you're sure you're logged in), and the
          real access control lives server-side regardless of which
          way someone arrives at the page. */}
      {user?.is_admin && (
        <Link to={ADMIN_PATH} className="inline-flex items-center gap-1" onClick={() => setMenuOpen(false)}>
          <ShieldCheck size={15} />
          {t("nav.adminDashboard")}
        </Link>
      )}
    </>
  );

  return (
    <header className="sticky top-0 z-50 border-b border-black/5 dark:border-white/10 bg-white/70 dark:bg-neutral-900/70 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 sm:px-6 py-3">
        {/* min-w-0 lets the logo text truncate/shrink instead of forcing
            the row to overflow — this plus hiding the desktop link
            cluster and controls behind the hamburger below max-md is
            what actually fixes small-screen overlap (previously nothing
            here collapsed at all, so the right-side controls just
            overlapped the logo on narrow viewports). */}
        <Link to="/" className="flex min-w-0 items-center gap-2 shrink-0" onClick={() => setMenuOpen(false)}>
          <img src="/logo/logo-full.png" alt="GT — GlobeTrotter" className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl shrink-0" />
          <span className="truncate text-base sm:text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
            GT<span style={{ color: "#C9975C" }}>Cam</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          {navLinks}
        </div>

        <div className="flex items-center gap-1.5 sm:gap-3">
          {/* Language/theme toggles collapse to icon-only + hide the
              language pill below sm, since a 2-3 letter pill plus a
              round icon plus username plus logout button all fighting
              for space is exactly what caused the overlap before. */}
          <button
            onClick={toggleLanguage}
            className="hidden sm:inline-flex rounded-full px-3 py-1 text-xs font-semibold border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
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

          {!loading && isAuthenticated && (
            <Link
              to="/profile?tab=Notifications"
              className="relative rounded-full p-2 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
              aria-label="Notifications"
            >
              <Bell size={16} />
              {unread > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold leading-none text-white">
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </Link>
          )}

          {/* Username + logout hide below md (they live inside the
              mobile drawer instead) so the top bar never has to fit
              more than logo + 3 icon buttons on a phone. */}
          {loading ? null : isAuthenticated ? (
            <div className="hidden md:flex items-center gap-3">
              <Link
  to="/profile"
  className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:underline"
>
  <UserAvatar user={user} />
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
              className="hidden md:inline-block rounded-full bg-teal-700 px-4 py-1.5 text-sm font-semibold text-white hover:bg-teal-800 transition"
            >
              {t("nav.login")}
            </Link>
          )}

          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="md:hidden rounded-full p-2 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="md:hidden border-t border-black/5 dark:border-white/10 bg-white dark:bg-neutral-900 px-4 py-4">
          <div className="flex flex-col gap-4 text-sm font-medium text-neutral-700 dark:text-neutral-200">
            {navLinks}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-black/5 dark:border-white/10 pt-4">
            <button
              onClick={toggleLanguage}
              className="rounded-full px-3 py-1 text-xs font-semibold border border-neutral-300 dark:border-neutral-600"
            >
              {i18n.language.startsWith("fr") ? "Français" : "English"}
            </button>
            {loading ? null : isAuthenticated ? (
              <div className="flex items-center gap-3">
                <Link to="/profile" onClick={() => setMenuOpen(false)} className="text-sm font-medium hover:underline">
                  {user?.username}
                </Link>
                <button
                  onClick={handleLogout}
                  className="rounded-full border border-neutral-300 dark:border-neutral-600 px-4 py-1.5 text-sm font-semibold"
                >
                  {t("nav.logout")}
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setMenuOpen(false)}
                className="rounded-full bg-teal-700 px-4 py-1.5 text-sm font-semibold text-white"
              >
                {t("nav.login")}
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
