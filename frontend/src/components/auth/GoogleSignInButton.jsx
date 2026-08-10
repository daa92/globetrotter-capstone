/**
 * src/components/auth/GoogleSignInButton.jsx
 *
 * Renders Google's own "Sign in with Google" button (via their Identity
 * Services script) and hands the resulting ID token to `onCredential`.
 *
 * Renders nothing at all if VITE_GOOGLE_CLIENT_ID isn't set — same
 * "absent rather than broken" pattern as the backend's own /auth/google
 * (which returns a clean 501 if GOOGLE_CLIENT_ID isn't configured)
 * rather than showing a button that's guaranteed to fail.
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

let scriptLoadPromise = null;
let loadedForLocale = null;
function loadGoogleScript(locale) {
  if (scriptLoadPromise && loadedForLocale === locale) return scriptLoadPromise;
  loadedForLocale = locale;
  scriptLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://accounts.google.com/gsi/client?hl=${locale}`;
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Could not load Google's sign-in script"));
    document.head.appendChild(script);
  });
  return scriptLoadPromise;
}

export default function GoogleSignInButton({ onCredential, onError }) {
  const { t, i18n } = useTranslation();
  const buttonRef = useRef(null);
  const [scriptError, setScriptError] = useState(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    let cancelled = false;
    loadGoogleScript(i18n.language)
      .then(() => {
        if (cancelled || !buttonRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => onCredential(response.credential),
        });
        buttonRef.current.innerHTML = ""; // clear before re-render (language change re-runs this effect)
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text: "continue_with",
        });
      })
      .catch((err) => {
        setScriptError(err.message);
        onError?.(err);
      });

    return () => {
      cancelled = true;
    };
  }, [onCredential, onError, i18n.language]);

  if (!GOOGLE_CLIENT_ID) {
    return (
      <p className="text-xs text-neutral-400 dark:text-neutral-500">
        {t("auth.googleNotConfigured")}
      </p>
    );
  }

  if (scriptError) {
    return <p className="text-xs text-red-500">{t("auth.googleLoadError")} {scriptError}</p>;
  }

  return <div ref={buttonRef} />;
}
