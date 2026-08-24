import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import Hero from "../components/layout/Hero";

export default function Home() {
  const { t } = useTranslation();
  return (
    <Hero>
      <h1 className="text-4xl md:text-6xl font-bold tracking-tight">{t("home.tagline")}</h1>
      <p className="mt-4 text-white/70 max-w-xl mx-auto">
        
      </p>
      <Link
        to="/explore"
        className="mt-8 inline-block rounded-full px-6 py-3 font-semibold transition"
        style={{ backgroundColor: "#C9975C", color: "#0F2027" }}
      >
        {t("home.cta")}
      </Link>
    </Hero>
  );
}
