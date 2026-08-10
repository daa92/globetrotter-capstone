import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register, registerPhone, verifyAccount } = useAuth();

  const [mode, setMode] = useState("email"); // "email" | "phone"
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Once registration succeeds, we switch straight into the verification
  // step — no separate page needed, and it keeps the "check your
  // email/SMS, code expires in 30 minutes" urgency front and center.
  const [awaitingVerification, setAwaitingVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError(t("auth.passwordsDontMatch"));
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "email") {
        await register({ username, email, password, preferences: [] });
      } else {
        await registerPhone({ username, phone, password, preferences: [] });
      }
      setAwaitingVerification(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifySubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await verifyAccount(verificationCode);
      navigate("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.invalidOrExpiredCode"));
    } finally {
      setSubmitting(false);
    }
  };

  if (awaitingVerification) {
    return (
      <section className="mx-auto flex max-w-md flex-col px-6 py-20">
        <h1 className="text-2xl font-bold">{t("auth.verifyTitle")}</h1>
        <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
          {mode === "email" ? t("auth.verifyBodyEmail") : t("auth.verifyBodyPhone")}
        </p>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleVerifySubmit} className="mt-6 space-y-4">
          <input
            type="text"
            required
            autoFocus
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value.trim())}
            placeholder={t("auth.verifyCodePlaceholder")}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
            style={{ backgroundColor: "#127C71" }}
          >
            {submitting ? t("auth.verifying") : t("auth.verifyAccountBtn")}
          </button>
        </form>
      </section>
    );
  }

  return (
    <section className="mx-auto flex max-w-md flex-col px-6 py-20">
      <h1 className="text-2xl font-bold">{t("nav.register")}</h1>

      <div className="mt-4 flex rounded-lg border border-neutral-300 dark:border-neutral-600 p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode("email")}
          className={`flex-1 rounded-md py-1.5 font-medium transition ${mode === "email" ? "text-white" : "text-neutral-500"}`}
          style={mode === "email" ? { backgroundColor: "#127C71" } : {}}
        >
          {t("auth.emailMode")}
        </button>
        <button
          type="button"
          onClick={() => setMode("phone")}
          className={`flex-1 rounded-md py-1.5 font-medium transition ${mode === "phone" ? "text-white" : "text-neutral-500"}`}
          style={mode === "phone" ? { backgroundColor: "#127C71" } : {}}
        >
          {t("auth.phoneMode")}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleRegisterSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="register-username" className="text-sm font-medium">{t("auth.username")}</label>
          <input
            id="register-username"
            type="text"
            required
            minLength={3}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
        </div>

        {mode === "email" ? (
          <div>
            <label htmlFor="register-email" className="text-sm font-medium">{t("auth.email")}</label>
            <input
              id="register-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
        ) : (
          <div>
            <label htmlFor="register-phone" className="text-sm font-medium">{t("auth.phone")}</label>
            <input
              id="register-phone"
              type="tel"
              required
              placeholder="+237650000000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
            />
          </div>
        )}

        <div>
          <label htmlFor="register-password" className="text-sm font-medium">{t("auth.password")}</label>
          <input
            id="register-password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
          <p className="mt-1 text-xs text-neutral-400">{t("auth.passwordHint")}</p>
        </div>

        <div>
          <label htmlFor="register-confirm-password" className="text-sm font-medium">{t("auth.confirmPassword")}</label>
          <input
            id="register-confirm-password"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
          style={{ backgroundColor: "#127C71" }}
        >
          {submitting ? t("auth.creatingAccount") : t("nav.register")}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
        {t("auth.alreadyHaveAccount")}{" "}
        <Link to="/login" className="text-teal-700 dark:text-teal-400 hover:underline">
          {t("nav.login")}
        </Link>
      </p>
    </section>
  );
}
