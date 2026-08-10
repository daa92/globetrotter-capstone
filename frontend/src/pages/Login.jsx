import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";
import GoogleSignInButton from "../components/auth/GoogleSignInButton";
import MfaChallengeForm from "../components/auth/MfaChallengeForm";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Once either password or Google login returns mfa_required, we hold
  // onto *how* to retry (which credential path) so the code-entry step
  // works the same regardless of which method got them here.
  const [pendingMfa, setPendingMfa] = useState(null); // { kind: "password" | "google", googleToken? }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(username, password);
      if (result.mfa_required) {
        setPendingMfa({ kind: "password" });
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleCredential = async (idToken) => {
    setError(null);
    setSubmitting(true);
    try {
      const result = await loginWithGoogle(idToken);
      if (result.mfa_required) {
        setPendingMfa({ kind: "google", googleToken: idToken });
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.googleSigninFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleMfaSubmit = async (code) => {
    setError(null);
    setSubmitting(true);
    try {
      const result =
        pendingMfa.kind === "google" ? await loginWithGoogle(pendingMfa.googleToken, code) : await login(username, password, code);
      if (!result.mfa_required) navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.invalidCode"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="mx-auto flex max-w-md flex-col px-6 py-20">
      <h1 className="text-2xl font-bold">{t("nav.login")}</h1>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 dark:bg-red-950/40 px-4 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {pendingMfa ? (
        <MfaChallengeForm onSubmit={handleMfaSubmit} submitting={submitting} />
      ) : (
        <>
          <form onSubmit={handlePasswordSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="login-username" className="text-sm font-medium">{t("auth.username")}</label>
              <input
                id="login-username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="text-sm font-medium">{t("auth.password")}</label>
                <Link to="/password-reset" className="text-xs text-teal-700 dark:text-teal-400 hover:underline">
                  {t("auth.forgotPassword")}
                </Link>
              </div>
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-600"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-50"
              style={{ backgroundColor: "#127C71" }}
            >
              {submitting ? t("auth.loggingIn") : t("nav.login")}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-neutral-400">
            <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
            {t("auth.or")}
            <div className="h-px flex-1 bg-neutral-200 dark:bg-neutral-700" />
          </div>

          <GoogleSignInButton onCredential={handleGoogleCredential} />

          <p className="mt-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
            {t("auth.noAccount")}{" "}
            <Link to="/register" className="text-teal-700 dark:text-teal-400 hover:underline">
              {t("nav.register")}
            </Link>
          </p>
        </>
      )}
    </section>
  );
}
