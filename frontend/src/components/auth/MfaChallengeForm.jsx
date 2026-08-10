import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function MfaChallengeForm({ onSubmit, submitting }) {
  const { t } = useTranslation();
  const [code, setCode] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(code);
      }}
      className="mt-4 space-y-3"
    >
      <p className="text-sm text-neutral-600 dark:text-neutral-300">{t("auth.mfaPrompt")}</p>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        required
        autoFocus
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        placeholder="000000"
        className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 text-center text-lg tracking-[0.3em] focus:outline-none focus:ring-2 focus:ring-teal-600"
      />
      <button
        type="submit"
        disabled={submitting || code.length !== 6}
        className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
        style={{ backgroundColor: "#127C71" }}
      >
        {submitting ? t("auth.verifying") : t("auth.verify")}
      </button>
    </form>
  );
}
