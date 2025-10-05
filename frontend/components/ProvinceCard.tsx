import { Province, DailyStats, ALERT_LEVEL_COLORS } from '@/types';
import { dataUtils } from '@/utils/api';
import { 
  MapPinIcon, 
  ExclamationTriangleIcon,
  CloudIcon,
  ChevronRightIcon 
} from '@heroicons/react/24/outline';
import Link from 'next/link';

interface ProvinceCardProps {
  province: Province;
  stats?: DailyStats;
  showDetails?: boolean;
  onClick?: () => void;
}

const ProvinceCard: React.FC<ProvinceCardProps> = ({
  province,
  stats,
  showDetails = false,
  onClick,
}) => {
  // Calculate alert level and air quality
  const alertLevel = stats 
    ? dataUtils.getAlertLevel(stats.pm25 || 0, stats.dust_event_detected, stats.dust_aod_mean)
    : 'none';
  
  const airQuality = stats?.pm25 ? dataUtils.getAirQualityCategory(stats.pm25) : 'No Data';
  const alertColor = ALERT_LEVEL_COLORS[alertLevel as keyof typeof ALERT_LEVEL_COLORS];
  
  // Get CSS class for air quality
  const getAirQualityClass = (quality: string) => {
    switch (quality) {
      case 'Good': return 'air-good';
      case 'Moderate': return 'air-moderate';
      case 'Unhealthy for Sensitive Groups': return 'air-unhealthy';
      case 'Unhealthy': return 'air-very-unhealthy';
      case 'Very Unhealthy': return 'air-very-unhealthy';
      case 'Hazardous': return 'air-hazardous';
      default: return '';
    }
  };

  const cardContent = (
    <div className={`province-card ${getAirQualityClass(airQuality)} transition-all duration-200`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center">
          <MapPinIcon className="h-5 w-5 text-gray-400 mr-2" />
          <div>
            <h3 className="font-semibold text-lg text-gray-900">{province.name}</h3>
            {province.region && (
              <p className="text-sm text-gray-500">{province.region}</p>
            )}
          </div>
        </div>
        
        {/* Alert indicator */}
        <div 
          className="w-4 h-4 rounded-full border-2 border-white shadow-sm"
          style={{ backgroundColor: alertColor }}
          title={`Alert level: ${alertLevel}`}
        />
      </div>

      {/* Main stats */}
      {stats ? (
        <div className="space-y-3">
          {/* PM2.5 value */}
          <div className="flex justify-between items-center">
            <span className="text-gray-600 font-medium">PM2.5:</span>
            <span className="text-xl font-bold" style={{ color: alertColor }}>
              {dataUtils.formatPM25(stats.pm25 || 0)}
            </span>
          </div>

          {/* Air quality category */}
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Air Quality:</span>
            <span className={`font-semibold text-sm px-2 py-1 rounded ${
              airQuality === 'Good' ? 'bg-green-100 text-green-800' :
              airQuality === 'Moderate' ? 'bg-yellow-100 text-yellow-800' :
              airQuality.includes('Unhealthy') ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {airQuality}
            </span>
          </div>

          {/* Dust status */}
          {stats.dust_event_detected && (
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-4 w-4 text-orange-500 mr-1" />
                <span className="text-sm text-gray-600">Dust Storm:</span>
              </div>
              <span className="text-sm font-semibold text-orange-600">
                {stats.dust_intensity || 'Tespit Edildi'}
              </span>
            </div>
          )}

          {showDetails && (
            <div className="pt-3 border-t border-gray-200 space-y-2">
              {/* AOD */}
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">AOD:</span>
                <span className="font-medium">{dataUtils.formatAOD(stats.aod_mean || 0)}</span>
              </div>

              {/* Dust AOD */}
              {stats.dust_aod_mean && stats.dust_aod_mean > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Dust AOD:</span>
                  <span className="font-medium">{dataUtils.formatAOD(stats.dust_aod_mean)}</span>
                </div>
              )}

              {/* Meteorological data */}
              {stats.rh_mean && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Humidity:</span>
                  <span className="font-medium">{Math.round(stats.rh_mean)}%</span>
                </div>
              )}

              {stats.blh_mean && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Boundary Layer:</span>
                  <span className="font-medium">{Math.round(stats.blh_mean)}m</span>
                </div>
              )}

              {/* Data quality */}
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Data Quality:</span>
                <span className="font-medium">
                  {Math.round((stats.data_quality_score || 0) * 100)}%
                </span>
              </div>
            </div>
          )}

          {/* Last update */}
          <div className="text-xs text-gray-500 pt-2">
            Last updated: {dataUtils.formatDate(stats.date)}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center py-8 text-gray-500">
          <CloudIcon className="h-8 w-8 mr-2" />
          <span>No data available</span>
        </div>
      )}

      {/* Action indicator */}
      {(onClick || !showDetails) && (
        <div className="flex justify-end mt-4 pt-3 border-t border-gray-200">
          <ChevronRightIcon className="h-5 w-5 text-gray-400" />
        </div>
      )}
    </div>
  );

  // Wrap with Link or div based on props
  if (onClick) {
    return (
      <div onClick={onClick} className="cursor-pointer">
        {cardContent}
      </div>
    );
  }

  if (!showDetails) {
    return (
      <Link href={`/province/${province.id}`} className="block">
        {cardContent}
      </Link>
    );
  }

  return cardContent;
};

export default ProvinceCard;
