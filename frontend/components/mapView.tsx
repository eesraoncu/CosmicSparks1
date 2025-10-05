import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Örnek veri
const cities = [
  { name: "Ankara", coords: [39.9208, 32.8541], pm25: 36 },
  { name: "Istanbul", coords: [41.0082, 28.9784], pm25: 55 },
  { name: "Izmir", coords: [38.4237, 27.1428], pm25: 25 },
  { name: "Diyarbakır", coords: [37.9144, 40.2306], pm25: 72 },
  { name: "Antalya", coords: [36.8969, 30.7133], pm25: 42 },
];

// Renk skalası
const getColor = (pm25: number) => {
  if (pm25 < 30) return "green";
  if (pm25 < 50) return "yellow";
  return "red";
};

export default function MapView() {
  return (
    <MapContainer
      center={[39.0, 35.0]} // Türkiye merkezi
      zoom={6}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {cities.map((city, i) => (
        <CircleMarker
          key={i}
          center={city.coords as [number, number]}
          radius={12}
          color={getColor(city.pm25)}
          fillOpacity={0.8}
        >
          <Popup>
            <strong>{city.name}</strong> <br />
            PM2.5: {city.pm25} μg/m³ <br />
            Risk:{" "}
            {getColor(city.pm25) === "green"
              ? "Low"
              : getColor(city.pm25) === "yellow"
              ? "Moderate"
              : "High"}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
