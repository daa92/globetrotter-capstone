import { useState } from "react";
import {
  Mountain, Palmtree, Landmark, Building2, PawPrint, Music, Waves,
  UtensilsCrossed, Coffee, Wine, Cross, Pill, Banknote, Fuel,
  GraduationCap, Film, Plane, ShoppingCart, BedDouble,
} from "lucide-react";

const CATEGORY_ICON = {
  // curated destination tags
  beach: Palmtree,
  hiking: Mountain,
  culture: Landmark,
  history: Landmark,
  wildlife: PawPrint,
  nightlife: Music,
  waterfall: Waves,
  city: Building2,
  // live POI categories (from /geo/poi)
  restaurant: UtensilsCrossed,
  fast_food: UtensilsCrossed,
  cafe: Coffee,
  bar: Wine,
  nightclub: Music,
  hospital: Cross,
  pharmacy: Pill,
  bank: Banknote,
  atm: Banknote,
  fuel: Fuel,
  school: GraduationCap,
  cinema: Film,
  hotel: BedDouble,
  guest_house: BedDouble,
  airport: Plane,
  supermarket: ShoppingCart,
  market: ShoppingCart,
};

const CATEGORY_GRADIENT = {
  beach: "from-amber-200 to-teal-600",
  hiking: "from-stone-300 to-teal-700",
  culture: "from-amber-300 to-stone-600",
  history: "from-amber-300 to-stone-600",
  wildlife: "from-lime-300 to-teal-700",
  nightlife: "from-purple-300 to-slate-700",
  waterfall: "from-sky-200 to-teal-700",
  city: "from-slate-300 to-slate-700",
  restaurant: "from-orange-200 to-red-700",
  fast_food: "from-orange-200 to-red-700",
  cafe: "from-amber-200 to-yellow-800",
  bar: "from-purple-300 to-fuchsia-800",
  nightclub: "from-purple-300 to-fuchsia-800",
  hospital: "from-red-200 to-rose-700",
  pharmacy: "from-emerald-200 to-emerald-700",
  bank: "from-slate-200 to-slate-600",
  atm: "from-slate-200 to-slate-600",
  fuel: "from-yellow-200 to-orange-700",
  school: "from-sky-200 to-blue-700",
  cinema: "from-indigo-300 to-slate-800",
  hotel: "from-teal-200 to-cyan-700",
  guest_house: "from-teal-200 to-cyan-700",
  airport: "from-sky-200 to-indigo-700",
  supermarket: "from-lime-200 to-green-700",
  market: "from-lime-200 to-green-700",
};

function pickCategory(tags = []) {
  return tags.find((t) => CATEGORY_ICON[t]) || tags[0] || "city";
}

/**
 * Renders destination.image_url if it's set and actually loads. If it's
 * missing, or fails to load (broken link, 404), falls back to a generated
 * gradient + icon card themed by the destination's first matching tag —
 * never a broken-image icon. This is deliberate: real photos for the seed
 * catalogue depend on external hosts we can't 100% guarantee stay up
 * forever, and user-submitted places (via POST /places) won't always
 * have a photo yet either.
 */
export default function DestinationImage({ destination, className = "" }) {
  const [failed, setFailed] = useState(false);
  const hasRealImage = destination.image_url && !failed;

  if (hasRealImage) {
    return (
      <img
        src={destination.image_url}
        alt={destination.name}
        className={className}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }

  const category = destination.category || pickCategory(destination.tags);
  const Icon = CATEGORY_ICON[category] || Building2;
  const gradient = CATEGORY_GRADIENT[category] || CATEGORY_GRADIENT.city;

  return (
    <div className={`flex items-center justify-center bg-gradient-to-br ${gradient} ${className}`}>
      <Icon className="h-10 w-10 text-white/90" strokeWidth={1.5} />
    </div>
  );
}
