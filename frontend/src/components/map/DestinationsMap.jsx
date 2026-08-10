import "./leafletIconFix";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import DestinationImage from "../destinations/DestinationImage";

// Roughly centers Cameroon in view at a zoom level that shows the whole country.
const CAMEROON_CENTER = [5.9, 12.5];
const DEFAULT_ZOOM = 6;

export default function DestinationsMap({ destinations, onSelect, height = "420px" }) {
  return (
    <div style={{ height }} className="w-full overflow-hidden rounded-2xl border border-neutral-200 dark:border-neutral-700">
      <MapContainer center={CAMEROON_CENTER} zoom={DEFAULT_ZOOM} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {destinations.map((d) => (
          <Marker
            key={d.id}
            position={[d.latitude, d.longitude]}
            eventHandlers={onSelect ? { click: () => onSelect(d) } : undefined}
          >
            <Popup>
              <div className="max-w-[200px]">
                <DestinationImage destination={d} className="mb-2 h-24 w-full rounded object-cover" />
                <p className="font-semibold">{d.name}</p>
                <p className="text-xs text-neutral-500">{d.region}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
