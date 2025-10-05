import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { Province, DailyStats } from '@/types';

interface DustMapProps {
  provinces: Province[];
  stats: DailyStats[];
  height?: string;
  interactive?: boolean;
  selectedProvince?: number;
  onProvinceSelect?: (provinceId: number) => void;
}

// Create a simple placeholder component
const MapPlaceholder = ({ height }: { height: string }) => (
  <div 
    className="bg-gradient-to-br from-blue-50 to-green-50 flex items-center justify-center rounded-lg border border-gray-200"
    style={{ height }}
  >
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p className="text-gray-600 font-medium">Loading Turkey Map...</p>
      <p className="text-sm text-gray-500 mt-2">🗺️ Live dust data is being prepared</p>
    </div>
  </div>
);

// Simple static map component as fallback
const StaticMap = ({ provinces, stats, height }: DustMapProps) => {
  // Get top provinces with highest PM2.5
  const topProvinces = stats
    .filter(stat => stat.pm25 !== undefined)
    .sort((a, b) => (b.pm25 || 0) - (a.pm25 || 0))
    .slice(0, 6)
    .map(stat => {
      const province = provinces.find(p => p.id === stat.province_id);
      return { province, stat };
    })
    .filter(item => item.province);

  const getStatusColor = (pm25: number) => {
    if (pm25 >= 50) return 'bg-red-500';
    if (pm25 >= 25) return 'bg-orange-500';
    if (pm25 >= 15) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getStatusText = (pm25: number) => {
    if (pm25 >= 50) return 'Unhealthy';
    if (pm25 >= 25) return 'Unhealthy for Sensitive Groups';
    if (pm25 >= 15) return 'Moderate';
    return 'Good';
  };

  return (
    <div 
      className="bg-white rounded-lg border border-gray-200 overflow-hidden"
      style={{ height }}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-green-600 text-white p-4">
        <h3 className="text-lg font-semibold flex items-center">
          🌍 Turkey Air Quality Status
        </h3>
        <p className="text-sm text-blue-100 mt-1">
          Real-time PM2.5 and dust concentration data
        </p>
      </div>

      {/* Status Grid */}
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {topProvinces.map(({ province, stat }, index) => (
            <div key={province?.id || index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">{province?.name}</h4>
                <div className={`w-3 h-3 rounded-full ${getStatusColor(stat?.pm25 || 0)}`}></div>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">PM2.5:</span>
                  <span className="font-semibold">{(stat?.pm25 || 0).toFixed(1)} μg/m³</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className={`font-semibold ${
                    (stat?.pm25 || 0) >= 50 ? 'text-red-600' : 
                    (stat?.pm25 || 0) >= 25 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {getStatusText(stat?.pm25 || 0)}
                  </span>
                </div>

                {stat?.dust_event_detected && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Dust:</span>
                    <span className="font-semibold text-orange-600">
                      {stat.dust_intensity || 'Detected'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <h4 className="font-medium text-gray-900 mb-3">PM2.5 Levels</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
              <span>Good (0-15)</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
              <span>Moderate (15-25)</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-orange-500 rounded-full mr-2"></div>
              <span>Unhealthy for Sensitive Groups (25-50)</span>
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
              <span>Unhealthy (50+)</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-gray-200 text-xs text-gray-500 text-center">
          <p>📡 Data Source: NASA MODIS, ECMWF CAMS | 🕐 Updated: {new Date().toLocaleString('en-US')}</p>
          <p className="mt-1">🌍 Loading interactive map...</p>
        </div>
      </div>
    </div>
  );
};

// Dynamic import of the actual map component
const DynamicLeafletMap = dynamic(
  () => import('./LeafletMap'),
  { 
    ssr: false,
    loading: () => <MapPlaceholder height="100%" />
  }
);

const DustMap: React.FC<DustMapProps> = (props) => {
  const [showMap, setShowMap] = useState(false);
  const [mapError, setMapError] = useState(false);

  useEffect(() => {
    // Add a delay to ensure client-side rendering
    const timer = setTimeout(() => {
      setShowMap(true);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Show static version on server or if map fails to load
  if (!showMap || mapError) {
    return (
      <div className="relative">
        <StaticMap {...props} />
        {showMap && (
          <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-lg">
            <div className="bg-white rounded-lg p-4 max-w-sm mx-4">
              <p className="text-center text-gray-700">
                🗺️ Loading interactive map...
              </p>
              <div className="mt-3 flex justify-center">
                <button
                  onClick={() => setMapError(true)}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Stay on static view
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Show dynamic map on client
  return (
    <div onError={() => setMapError(true)}>
      <DynamicLeafletMap {...props} />
    </div>
  );
};

export default DustMap;