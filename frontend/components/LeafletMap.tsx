import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Province, DailyStats, PROVINCE_CENTERS, ALERT_LEVEL_COLORS } from '@/types';
import { dataUtils } from '@/utils/api';

// Fix for default markers in Next.js
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: '/leaflet/marker-icon-2x.png',
    iconUrl: '/leaflet/marker-icon.png',
    shadowUrl: '/leaflet/marker-shadow.png',
  });
}

interface LeafletMapProps {
  provinces: Province[];
  stats: DailyStats[];
  height?: string;
  interactive?: boolean;
  selectedProvince?: number;
  onProvinceSelect?: (provinceId: number) => void;
}

// Custom marker component
const ProvinceMarker = ({ 
  province, 
  stats, 
  onSelect 
}: { 
  province: Province; 
  stats?: DailyStats; 
  onSelect?: (provinceId: number) => void;
}) => {
  const position = PROVINCE_CENTERS[province.id] || [39.9334, 32.8597];
  
  if (!position) return null;

  // Calculate alert level and color
  const alertLevel = stats 
    ? dataUtils.getAlertLevel(stats.pm25 || 0, stats.dust_event_detected, stats.dust_aod_mean)
    : 'none';
  
  const color = ALERT_LEVEL_COLORS[alertLevel as keyof typeof ALERT_LEVEL_COLORS];
  
  // Create custom icon
  const customIcon = L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 10px;
        font-weight: bold;
      ">
        ${province.id}
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });

  const airQuality = stats?.pm25 ? dataUtils.getAirQualityCategory(stats.pm25) : 'No Data';
  const isForecast = stats?.data_quality_score === 0.7;
  
  return (
    <Marker 
      position={position} 
      icon={customIcon}
      eventHandlers={{
        click: () => onSelect && onSelect(province.id),
      }}
    >
      <Popup className="province-popup">
        <div className="p-3 min-w-[200px]">
          <h3 className="font-bold text-lg mb-2">{province.name}</h3>
          
          {isForecast && (
            <div className="mb-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full inline-block">
              📊 Forecast Data
            </div>
          )}
          
          {stats ? (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">PM2.5:</span>
                <span className="font-semibold">
                  {dataUtils.formatPM25(stats.pm25 || 0)}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Air Quality:</span>
                <span className={`font-semibold ${
                  airQuality === 'Good' ? 'text-green-600' :
                  airQuality === 'Moderate' ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {airQuality}
                </span>
              </div>
              
              {stats.dust_event_detected && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Dust Status:</span>
                  <span className="font-semibold text-orange-600">
                    {stats.dust_intensity || 'Detected'}
                  </span>
                </div>
              )}
              
              <div className="flex justify-between">
                <span className="text-gray-600">AOD:</span>
                <span className="font-semibold">
                  {dataUtils.formatAOD(stats.aod_mean || 0)}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Data Quality:</span>
                <span className="font-semibold">
                  {Math.round((stats.data_quality_score || 0) * 100)}%
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No data available</p>
          )}
          
          <div className="mt-3 pt-2 border-t border-gray-200">
            <button 
              onClick={() => onSelect && onSelect(province.id)}
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              View Details →
            </button>
          </div>
        </div>
      </Popup>
    </Marker>
  );
};

// Map update component
const MapUpdater = ({ 
  selectedProvince 
}: { 
  selectedProvince?: number 
}) => {
  const map = useMap();
  
  useEffect(() => {
    if (selectedProvince && PROVINCE_CENTERS[selectedProvince]) {
      const position = PROVINCE_CENTERS[selectedProvince];
      map.setView(position, 8, { animate: true });
    }
  }, [selectedProvince, map]);
  
  return null;
};

// Legend component
const MapLegend = () => {
  const legendItems = [
    { level: 'none', color: ALERT_LEVEL_COLORS.none, label: 'Good (0-8 μg/m³)' },
    { level: 'low', color: ALERT_LEVEL_COLORS.low, label: 'Moderate (8-15 μg/m³)' },
    { level: 'moderate', color: ALERT_LEVEL_COLORS.moderate, label: 'Unhealthy for Sensitive Groups (15-25 μg/m³)' },
    { level: 'high', color: ALERT_LEVEL_COLORS.high, label: 'Unhealthy (25-50 μg/m³)' },
    { level: 'extreme', color: ALERT_LEVEL_COLORS.extreme, label: 'Hazardous (50+ μg/m³)' },
  ];

  return (
    <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-4 z-[1000] max-w-xs">
      <h4 className="font-semibold text-sm mb-3">PM2.5 Levels</h4>
      <div className="space-y-2">
        {legendItems.map((item) => (
          <div key={item.level} className="flex items-center text-xs">
            <div 
              className="w-4 h-4 rounded-full mr-2 border border-white shadow-sm"
              style={{ backgroundColor: item.color }}
            />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-2 border-t border-gray-200 text-xs text-gray-500">
        <p>Source: NASA MODIS, ECMWF CAMS</p>
        <p>Updated: {new Date().toLocaleDateString('en-US')}</p>
      </div>
    </div>
  );
};

const LeafletMap: React.FC<LeafletMapProps> = ({
  provinces,
  stats,
  height = '100%',
  interactive = true,
  selectedProvince,
  onProvinceSelect,
}) => {
  // Turkey bounds
  const turkeyBounds: [number, number][] = [
    [35.5, 25.5], // Southwest
    [42.5, 45.0], // Northeast
  ];

  return (
    <div className="relative" style={{ height }}>
      <MapContainer
        bounds={turkeyBounds}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={interactive}
        dragging={interactive}
        zoomControl={interactive}
        doubleClickZoom={interactive}
        boxZoom={interactive}
        keyboard={interactive}
        className="rounded-lg"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* Province markers */}
        {provinces.map((province) => {
          const provinceStats = stats.find(s => s.province_id === province.id);
          return (
            <ProvinceMarker
              key={province.id}
              province={province}
              stats={provinceStats}
              onSelect={onProvinceSelect}
            />
          );
        })}
        
        {/* Map updater for selected province */}
        <MapUpdater selectedProvince={selectedProvince} />
      </MapContainer>
      
      {/* Legend */}
      <MapLegend />
      
      {/* Status indicator */}
      <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-3 z-[1000]">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-sm font-medium">Live Data</span>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  );
};

export default LeafletMap;
