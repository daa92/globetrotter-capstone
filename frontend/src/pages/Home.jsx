import { useTranslation } from "react-i18next";

export default function Home() {
  const { t } = useTranslation();
  return (
    <section className="mx-auto max-w-6xl px-6 py-24 text-center">
      <h1 className="text-4xl md:text-5xl font-bold tracking-tight">{t("home.tagline")}</h1>
      <p className="mt-4 text-neutral-500 dark:text-neutral-400">
        Placeholder homepage — real hero design coming once we lock in the visual direction.
      </p>
      <a
        href="/explore"
        className="mt-8 inline-block rounded-full bg-teal-700 px-6 py-3 text-white font-semibold hover:bg-teal-800 transition"
      >
        {t("home.cta")}
      </a>
    </section>
  );
}
