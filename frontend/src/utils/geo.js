/**
 * src/utils/geo.js
 *
 * Haversine formula — great-circle distance between two lat/lng points,
 * in kilometers. Used client-side for the "how far" filter (distance
 * from the user's current location, via the browser's Geolocation API)
 * since our destination catalogue is small enough that computing this
 * for every item on every filter change is instant — no backend round
 * trip needed for this.
 */
const EARTH_RADIUS_KM = 6371;

function toRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

export function haversineDistanceKm(lat1, lon1, lat2, lon2) {
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_KM * c;
}
