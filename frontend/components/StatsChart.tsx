import React from 'react';

interface StatsData {
  province: string;
  pm25: number;
  aod: number;
  dustDetected: boolean;
}

interface StatsChartProps {
  data: StatsData[];
}

const StatsChart: React.FC<StatsChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          📊 Air Quality Statistics
        </h3>
        <div className="text-gray-500 text-center py-8">
          Loading data...
        </div>
      </div>
    );
  }

  const maxPM25 = Math.max(...data.map(d => d.pm25));
  const maxAOD = Math.max(...data.map(d => d.aod));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        📊 Air Quality Statistics
      </h3>
      
      <div className="space-y-4">
        {data.slice(0, 5).map((item, index) => (
          <div key={index} className="border-b border-gray-200 pb-3 last:border-b-0">
            <div className="flex justify-between items-center mb-2">
              <span className="font-medium text-gray-700">{item.province}</span>
              {item.dustDetected && (
                <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded-full">
                  🌪️ Dust
                </span>
              )}
            </div>
            
            {/* PM2.5 Bar */}
            <div className="mb-2">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>PM2.5</span>
                <span>{item.pm25.toFixed(1)} μg/m³</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    item.pm25 > 50 ? 'bg-red-500' : 
                    item.pm25 > 35 ? 'bg-orange-500' : 
                    item.pm25 > 25 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${(item.pm25 / maxPM25) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* AOD Bar */}
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>AOD</span>
                <span>{item.aod.toFixed(3)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-blue-500"
                  style={{ width: `${(item.aod / maxAOD) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {data.length > 5 && (
        <div className="text-center text-sm text-gray-500 mt-4">
          +{data.length - 5} more provinces...
        </div>
      )}

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="text-sm text-gray-600">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Good (0-25)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span>Moderate (25-35)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-500 rounded"></div>
              <span>Unhealthy for Sensitive Groups (35-50)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Unhealthy (50+)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsChart;
