import { useTranslation } from "react-i18next";

export default function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="border-t border-black/5 dark:border-white/10 mt-24 py-8">
      <div className="mx-auto max-w-6xl px-6 flex items-center justify-between text-sm text-neutral-500 dark:text-neutral-400">
        <img src="/logo/logo-full.png" alt="GTCam" className="h-8 w-8 rounded-lg opacity-80" />
        <span>© {new Date().getFullYear()} GTCam. {t("footer.rights")}</span>
      </div>
    </footer>
  );
}
