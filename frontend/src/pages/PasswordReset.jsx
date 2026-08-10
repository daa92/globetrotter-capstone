import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function PasswordReset() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { requestPasswordReset, confirmPasswordReset } = useAuth();

  const [step, setStep] = useState("request"); // "request" | "confirm"
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleRequest = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await requestPasswordReset(username);
      setMessage(result.detail);
      setStep("confirm");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await confirmPasswordReset(code, newPassword);
      navigate("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.invalidOrExpiredReset"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="mx-auto flex max-w-md flex-col px-6 py-20">
      <h1 className="text-2xl font-bold">{t("auth.resetTitle")}</h1>

      {message && step === "confirm" && (
        <div className="mt-4 rounded-lg bg-teal-50 dark:bg-teal-950/40 px-4 py-2 text-sm text-teal-700 dark:text-teal-300">
          {message}
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {step === "request" ? (
        <form onSubmit={handleRequest} className="mt-6 space-y-4">
          <div>
            <label htmlFor="reset-username" className="text-sm font-medium">{t("auth.username")}</label>
            <input
              id="reset-username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
            style={{ backgroundColor: "#127C71" }}
          >
            {submitting ? t("auth.sending") : t("auth.sendResetCode")}
          </button>
        </form>
      ) : (
        <form onSubmit={handleConfirm} className="mt-6 space-y-4">
          <div>
            <label htmlFor="reset-code" className="text-sm font-medium">{t("auth.resetCode")}</label>
            <input
              id="reset-code"
              type="text"
              required
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value.trim())}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
          <div>
            <label htmlFor="reset-new-password" className="text-sm font-medium">{t("auth.newPassword")}</label>
            <input
              id="reset-new-password"
              type="password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
            style={{ backgroundColor: "#127C71" }}
          >
            {submitting ? t("auth.updating") : t("auth.setNewPassword")}
          </button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
        <Link to="/login" className="text-teal-700 dark:text-teal-400 hover:underline">
          {t("auth.backToLogin")}
        </Link>
      </p>
    </section>
  );
}
