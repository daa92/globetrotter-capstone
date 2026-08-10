/**
 * src/components/map/leafletIconFix.js
 *
 * Leaflet's default marker icon references image paths that assume a
 * traditional (non-bundled) script-tag setup — under Vite (and webpack,
 * and basically every modern bundler), those paths 404 and markers
 * render as broken images. This is a well-documented Leaflet+bundler
 * issue, not a mistake in how the map is used — the fix is to import
 * the marker images explicitly and re-point Leaflet's default icon at
 * the bundled URLs. Import this once, before any map renders.
 */
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});
