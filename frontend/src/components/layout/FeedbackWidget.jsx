import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MessageSquarePlus, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { submitFeedback, ApiError } from "../../api/client";

const CATEGORIES = ["bug", "suggestion", "place_report", "other"];

// Mounted once in Layout.jsx (outside <main>, alongside Navbar/Footer) so
// it's fixed bottom-right and persists across every route — it's UI
// chrome, not page content, same reasoning as the Navbar itself.
export default function FeedbackWidget() {
  const { t } = useTranslation();
  const { user, accessToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("suggestion");
  const [message, setMessage] = useState("");
  const [rating, setRating] = useState(0);
  const [status, setStatus] = useState("idle"); // idle | sending | sent | error
  const [error, setError] = useState(null);

  const reset = () => {
    setCategory("suggestion");
    setMessage("");
    setRating(0);
    setStatus("idle");
    setError(null);
  };

  const close = () => {
    setOpen(false);
    // Small delay avoids a visible content flash while the panel animates out.
    setTimeout(reset, 200);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus("sending");
    setError(null);
    try {
      await submitFeedback(accessToken, {
        category,
        message,
        rating: rating > 0 ? rating : undefined,
      });
      setStatus("sent");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
      setStatus("error");
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label={t("feedback.buttonLabel")}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-teal-600 hover:bg-teal-700 text-white px-4 py-3 shadow-lg shadow-black/20 transition-transform hover:scale-105"
      >
        <MessageSquarePlus size={18} />
        <span className="hidden sm:inline text-sm font-medium">{t("feedback.buttonLabel")}</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:justify-end p-0 sm:p-6">
          {/* backdrop */}
          <div className="absolute inset-0 bg-black/40" onClick={close} />

          <div className="relative w-full sm:w-96 max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 shadow-xl p-5">
            <button
              onClick={close}
              aria-label={t("feedback.close")}
              className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
            >
              <X size={18} />
            </button>

            <h2 className="text-lg font-semibold pr-6">{t("feedback.title")}</h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{t("feedback.subtitle")}</p>

            {!user ? (
              <p className="mt-6 text-sm text-neutral-600 dark:text-neutral-300">
                {t("feedback.loginRequired")}{" "}
                <Link to="/login" onClick={close} className="text-teal-700 dark:text-teal-400 hover:underline">
                  {t("feedback.loginLink")}
                </Link>
              </p>
            ) : status === "sent" ? (
              <div className="mt-6 rounded-lg bg-teal-50 dark:bg-teal-950/40 px-4 py-3 text-sm text-teal-700 dark:text-teal-300">
                {t("feedback.success")}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    {t("feedback.category")}
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setCategory(c)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                          category === c
                            ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                            : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
                        }`}
                      >
                        {t(`feedback.category${c === "place_report" ? "PlaceReport" : c[0].toUpperCase() + c.slice(1)}`)}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    {t("feedback.message")}
                  </label>
                  <textarea
                    required
                    minLength={5}
                    maxLength={2000}
                    rows={4}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder={t("feedback.messagePlaceholder")}
                    className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
                    {t("feedback.rating")}
                  </label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setRating(rating === n ? 0 : n)}
                        aria-label={String(n)}
                        className={`h-8 w-8 rounded-md text-sm font-medium ${
                          n <= rating
                            ? "bg-amber-400 text-white"
                            : "bg-neutral-100 dark:bg-neutral-800 text-neutral-400"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>

                {error && <p className="text-sm text-red-500">{error}</p>}

                <button
                  type="submit"
                  disabled={status === "sending"}
                  className="w-full rounded-lg bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white py-2 text-sm font-medium"
                >
                  {status === "sending" ? t("feedback.sending") : t("feedback.submit")}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
