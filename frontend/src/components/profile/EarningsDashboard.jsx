import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import * as api from "../../api/client";
import { ApiError } from "../../api/client";

function RequirementRow({ label, req }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-neutral-600 dark:text-neutral-300">{label}</span>
      <span className={req.met ? "text-teal-600 dark:text-teal-400" : "text-neutral-400"}>
        {req.have} / {req.need} {req.met ? "✓" : ""}
      </span>
    </div>
  );
}

export default function EarningsDashboard({ accessToken }) {
  const { t } = useTranslation();
  const [earnings, setEarnings] = useState(null);
  const [error, setError] = useState(null);
  const [requesting, setRequesting] = useState(false);
  const [payoutMessage, setPayoutMessage] = useState(null);

  const load = async () => {
    setError(null);
    try {
      setEarnings(await api.getEarnings(accessToken));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
    }
  };

  useEffect(() => {
    if (accessToken) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!earnings) return <p className="text-neutral-400">{t("earnings.loading")}</p>;

  const chartData = earnings.daily_log.map((d) => ({
    date: d.date.slice(5),
    seconds: d.active_seconds,
    qualified: d.qualified,
  }));

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{t("earnings.totalEarned")}</p>
          <p className="mt-1 text-3xl font-bold" style={{ color: "#127C71" }}>
            ${earnings.total_earned_usd}
          </p>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            {earnings.available_fcfa.toLocaleString()} FCFA {t("earnings.available")}
          </p>
        </div>
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{t("earnings.qualifyingDays")}</p>
          <p className="mt-1 text-3xl font-bold">{earnings.qualifying_days}</p>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            ${earnings.usage_earnings_usd} {t("earnings.fromUsage")} · ${earnings.referral_earnings_usd}{" "}
            {t("earnings.fromReferrals", { count: earnings.referral_count })}
          </p>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <p className="mb-3 text-sm font-medium">{t("earnings.dailyActivity")}</p>
        {chartData.length === 0 ? (
          <p className="text-sm text-neutral-400">{t("earnings.noActivity")}</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => [`${value}s`, t("earnings.dailyActivity")]} />
              <Bar dataKey="seconds" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.qualified ? "#127C71" : "#C9975C"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="mt-6 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <p className="mb-3 text-sm font-medium">{t("earnings.referralLink")}</p>
        <div className="flex items-center gap-2">
          <input
            readOnly
            value={earnings.referral_link}
            className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-transparent px-3 py-1.5 text-sm"
          />
          <button
            onClick={() => navigator.clipboard.writeText(earnings.referral_link)}
            className="rounded-lg border border-neutral-300 dark:border-neutral-600 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            {t("earnings.copy")}
          </button>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
        <p className="mb-3 text-sm font-medium">{t("earnings.payoutEligibility")}</p>
        <div className="space-y-2">
          <RequirementRow label={t("earnings.balance")} req={earnings.payout_eligibility.balance} />
          <RequirementRow label={t("earnings.referrals")} req={earnings.payout_eligibility.referrals} />
          <RequirementRow label={t("earnings.goodFeedback")} req={earnings.payout_eligibility.good_feedback} />
        </div>
        {payoutMessage && <p className="mt-3 text-sm text-teal-600 dark:text-teal-400">{payoutMessage}</p>}
        <button
          disabled={!earnings.payout_eligibility.eligible || requesting}
          onClick={async () => {
            setRequesting(true);
            setPayoutMessage(null);
            try {
              const result = await api.requestPayout(accessToken);
              setPayoutMessage(t("earnings.payoutRequested", { amount: result.amount_usd, status: result.status }));
              await load();
            } catch (err) {
              setPayoutMessage(err instanceof ApiError ? err.detail : t("earnings.payoutError"));
            } finally {
              setRequesting(false);
            }
          }}
          className="mt-4 w-full rounded-lg py-2 font-semibold text-white transition disabled:opacity-40"
          style={{ backgroundColor: "#127C71" }}
        >
          {requesting ? t("earnings.requesting") : t("earnings.requestPayout")}
        </button>
      </div>
    </div>
  );
}
