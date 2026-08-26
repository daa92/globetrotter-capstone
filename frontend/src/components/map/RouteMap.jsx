import "./leafletIconFix";
import { MapContainer, Marker, Popup, Polyline, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";

const CAMEROON_CENTER = [5.9, 12.5];
const DEFAULT_ZOOM = 6;

// react-leaflet doesn't auto-recenter when data arrives after the map
// first mounts (e.g. a route computed a second later) — this fits the
// view to whatever stops exist, every time the list changes.
function FitToStops({ stops }) {
  const map = useMap();
  useEffect(() => {
    if (stops.length === 0) return;
    if (stops.length === 1) {
      map.setView([stops[0].latitude, stops[0].longitude], 11);
    } else {
      map.fitBounds(stops.map((s) => [s.latitude, s.longitude]), { padding: [30, 30] });
    }
  }, [stops, map]);
  return null;
}

/**
 * `stops`: ordered [{ name, latitude, longitude }] — first entry is the
 * start point if one was chosen. `geometry`: optional [[lat,lng], ...]
 * road-following polyline from OpenRouteService; when empty (no
 * OPENROUTESERVICE_API_KEY configured), falls back to a straight line
 * connecting the stops in order, clearly styled dashed so it doesn't
 * look like a claimed real route.
 */
export default function RouteMap({ stops, geometry, height = "360px" }) {
  const hasRealGeometry = geometry && geometry.length > 0;
  const fallbackLine = stops.map((s) => [s.latitude, s.longitude]);

  return (
    <div style={{ height }} className="w-full overflow-hidden rounded-2xl border border-neutral-200 dark:border-neutral-700">
      <MapContainer center={CAMEROON_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToStops stops={stops} />

        {hasRealGeometry ? (
          <Polyline positions={geometry} pathOptions={{ color: "#1F7A4D", weight: 4, opacity: 0.85 }} />
        ) : (
          stops.length > 1 && (
            <Polyline positions={fallbackLine} pathOptions={{ color: "#C1502E", weight: 3, opacity: 0.7, dashArray: "6 8" }} />
          )
        )}

        {stops.map((s, i) => (
          <Marker key={`${s.name}-${i}`} position={[s.latitude, s.longitude]}>
            <Popup>
              <p className="font-semibold text-sm">{i === 0 && stops.length > 1 ? "🚩 " : `${i}. `}{s.name}</p>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
