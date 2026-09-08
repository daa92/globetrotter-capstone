import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/0029VbDGgQPKrWQxtxeC1f26";

/** The official WhatsApp glyph (phone handset inside a speech bubble) —
 * same outline used everywhere WhatsApp itself links out from a site,
 * drawn as inline SVG so it renders crisply at any size with no image
 * request. Mounted once in Layout.jsx, fixed bottom-left so it never
 * collides with FeedbackWidget's bottom-right button — except on /chat,
 * where the message composer already lives in that corner, so it hides
 * itself there instead of floating on top of the attach/send buttons. */
export default function WhatsAppButton() {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  if (pathname.startsWith("/chat")) return null;

  return (
    <a
      href={WHATSAPP_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={t("whatsapp.follow", "Follow our WhatsApp channel")}
      title={t("whatsapp.follow", "Follow our WhatsApp channel")}
      className="fixed bottom-6 left-6 z-40 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition hover:scale-105 hover:shadow-xl"
      style={{ backgroundColor: "#25D366" }}
    >
      <svg viewBox="0 0 32 32" className="h-7 w-7 fill-white" aria-hidden="true">
        <path d="M16.001 3.2c-7.06 0-12.8 5.74-12.8 12.8 0 2.258.593 4.472 1.72 6.418L3.2 28.8l6.56-1.68a12.74 12.74 0 0 0 6.24 1.63h.005c7.06 0 12.8-5.74 12.8-12.8s-5.74-12.75-12.804-12.75Zm0 23.36h-.004a10.55 10.55 0 0 1-5.383-1.474l-.386-.23-3.893.997 1.04-3.796-.252-.39a10.53 10.53 0 0 1-1.62-5.667c0-5.83 4.746-10.576 10.582-10.576 2.827 0 5.484 1.102 7.482 3.102a10.5 10.5 0 0 1 3.097 7.482c0 5.83-4.746 10.552-10.663 10.552Zm5.797-7.905c-.318-.16-1.882-.929-2.174-1.035-.291-.107-.503-.16-.715.16s-.821 1.035-1.006 1.248c-.185.213-.371.24-.688.08-.318-.16-1.341-.494-2.554-1.575-.944-.842-1.582-1.882-1.767-2.2-.185-.318-.02-.49.14-.649.143-.142.318-.371.477-.557.16-.186.212-.318.318-.53.106-.213.053-.4-.027-.56-.08-.16-.715-1.722-.98-2.359-.258-.62-.52-.536-.715-.546l-.61-.01c-.212 0-.557.08-.848.4-.291.318-1.113 1.088-1.113 2.652s1.14 3.075 1.3 3.287c.16.213 2.244 3.424 5.435 4.803.759.328 1.352.524 1.815.671.762.242 1.456.208 2.005.126.612-.091 1.882-.769 2.147-1.512.265-.743.265-1.38.185-1.512-.08-.132-.291-.213-.61-.373Z" />
      </svg>
    </a>
  );
}
