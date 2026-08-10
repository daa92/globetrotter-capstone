import { useTranslation } from "react-i18next";
import { UserPlus, Search, Sparkles, MapPinned, Coins, Share2, MessageSquare } from "lucide-react";

const STEP_ICONS = [UserPlus, Search, Sparkles, MapPinned, Coins, Share2, MessageSquare];

export default function HowToUse() {
  const { t } = useTranslation();
  const steps = STEP_ICONS.map((icon, i) => ({
    icon,
    title: t(`howToUse.step${i + 1}Title`),
    body: t(`howToUse.step${i + 1}Body`),
  }));

  return (
    <section className="mx-auto max-w-4xl px-6 py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold">{t("howToUse.aboutTitle")}</h1>
        <p className="mx-auto mt-4 max-w-2xl text-neutral-600 dark:text-neutral-300">{t("howToUse.aboutBody")}</p>
      </div>

      <h2 className="mt-16 text-center text-2xl font-bold">{t("howToUse.howItWorks")}</h2>
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-6">
        {steps.map((step, i) => (
          <div key={step.title} className="flex gap-4 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
            <div
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white"
              style={{ backgroundColor: "#127C71" }}
            >
              <step.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold">
                {i + 1}. {step.title}
              </p>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{step.body}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-16 rounded-2xl p-8 text-center text-white" style={{ backgroundColor: "#0F2027" }}>
        <p className="text-lg font-semibold" style={{ color: "#C9975C" }}>
          {t("howToUse.noInvestment")}
        </p>
        <p className="mt-2 text-sm text-white/70">{t("howToUse.freeToUse")}</p>
      </div>
    </section>
  );
}
