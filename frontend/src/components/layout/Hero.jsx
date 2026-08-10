import { useState } from "react";

/**
 * Homepage hero background. Looks for, in order of preference:
 *   1. /media/hero/hero-bg.mp4   (video, muted/looping)
 *   2. /media/hero/hero-bg.jpg   (static image — used as the video's poster,
 *                                  and as the fallback if there's no video yet)
 *   3. a plain brand-gradient div (what you'll see until either file exists)
 *
 * You never need to touch this file to add your hero media — just drop
 * files at those exact paths (see public/media/hero/README.md) and they
 * appear automatically, because both onError handlers below silently fall
 * back a level instead of showing a broken-image/video icon.
 */
export default function Hero({ children }) {
  const [videoFailed, setVideoFailed] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const showVideo = !videoFailed;
  const showImageFallback = videoFailed && !imageFailed;

  return (
    <div className="relative overflow-hidden min-h-[70vh] flex items-center">
      {/* Brand-gradient base layer — always present, so there's never a
          blank/broken look no matter which media files exist yet. */}
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(160deg, #0F2027 0%, #1B2E32 55%, #23393F 100%)",
        }}
      />

      {showVideo && (
        <video
          className="absolute inset-0 h-full w-full object-cover opacity-60"
          src="/media/hero/hero-bg.mp4"
          poster="/media/hero/hero-bg.jpg"
          autoPlay
          muted
          loop
          playsInline
          onError={() => setVideoFailed(true)}
        />
      )}

      {showImageFallback && (
        <img
          className="absolute inset-0 h-full w-full object-cover opacity-60"
          src="/media/hero/hero-bg.jpg"
          alt=""
          onError={() => setImageFailed(true)}
        />
      )}

      <div className="relative z-10 mx-auto max-w-6xl px-6 text-center text-white">
        {children}
      </div>
    </div>
  );
}
