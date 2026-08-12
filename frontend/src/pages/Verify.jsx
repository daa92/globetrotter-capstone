import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

// Reached by clicking the verification link emailed on sign-up
// (?token=... appended by the backend — see _verification_email_html in
// app/routers/auth.py). This calls the same POST /auth/verify endpoint
// the in-app manual-code screen uses; either path works standalone.
export default function Verify() {
  const { t } = useTranslation();
  const { verifyAccount } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState(token ? "verifying" : "missing"); // "verifying" | "success" | "error" | "missing"
  const [error, setError] = useState(null);
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true; // StrictMode/re-render guard — token is one-time-use server-side
    (async () => {
      try {
        await verifyAccount(token);
        setStatus("success");
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : t("auth.invalidOrExpiredCode"));
        setStatus("error");
      }
    })();
  }, [token, verifyAccount, t]);

  return (
    <section className="mx-auto flex max-w-md flex-col px-6 py-20 text-center">
      <h1 className="text-2xl font-bold">{t("auth.verifyTitle")}</h1>

      {status === "verifying" && (
        <p className="mt-4 text-sm text-neutral-500 dark:text-neutral-400">{t("auth.verifying")}</p>
      )}

      {status === "missing" && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {t("auth.invalidOrExpiredCode")}
        </div>
      )}

      {status === "success" && (
        <div className="mt-4 rounded-lg bg-teal-50 dark:bg-teal-950/40 px-4 py-2 text-sm text-teal-700 dark:text-teal-300">
          {t("auth.verifyAccountBtn")} ✓
        </div>
      )}

      {status === "error" && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {(status === "success" || status === "error" || status === "missing") && (
        <p className="mt-6 text-sm text-neutral-500 dark:text-neutral-400">
          <Link to="/login" className="text-teal-700 dark:text-teal-400 hover:underline">
            {t("auth.backToLogin")}
          </Link>
        </p>
      )}
    </section>
  );
}
