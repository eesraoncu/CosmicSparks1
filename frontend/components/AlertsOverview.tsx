import { useState, useMemo } from 'react';
import { Province, DailyStats, ALERT_LEVEL_COLORS, ALERT_LEVEL_LABELS } from '@/types';
import { dataUtils } from '@/utils/api';
import { 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon 
} from '@heroicons/react/24/outline';

interface AlertsOverviewProps {
  stats: DailyStats[];
  provinces: Province[];
}

interface AlertSummary {
  level: string;
  count: number;
  provinces: Array<{ province: Province; stats: DailyStats }>;
  color: string;
  label: string;
}

const AlertsOverview: React.FC<AlertsOverviewProps> = ({ stats, provinces }) => {
  const [expandedLevel, setExpandedLevel] = useState<string | null>(null);

  // Group alerts by level
  const alertSummary = useMemo(() => {
    const summary: Record<string, AlertSummary> = {};

    stats.forEach(stat => {
      const province = provinces.find(p => p.id === stat.province_id);
      if (!province) return;

      const alertLevel = dataUtils.getAlertLevel(
        stat.pm25 || 0, 
        stat.dust_event_detected, 
        stat.dust_aod_mean
      );

      if (!summary[alertLevel]) {
        summary[alertLevel] = {
          level: alertLevel,
          count: 0,
          provinces: [],
          color: ALERT_LEVEL_COLORS[alertLevel as keyof typeof ALERT_LEVEL_COLORS],
          label: ALERT_LEVEL_LABELS[alertLevel as keyof typeof ALERT_LEVEL_LABELS]
        };
      }

      summary[alertLevel].count++;
      summary[alertLevel].provinces.push({ province, stats: stat });
    });

    // Sort by severity (extreme first)
    const levelOrder = ['extreme', 'high', 'moderate', 'low', 'none'];
    return levelOrder
      .filter(level => summary[level])
      .map(level => summary[level]);
  }, [stats, provinces]);

  // Get overall status
  const getOverallStatus = () => {
    const highRiskCount = alertSummary
      .filter(alert => ['extreme', 'high'].includes(alert.level))
      .reduce((sum, alert) => sum + alert.count, 0);

    if (highRiskCount > 0) {
      return {
        status: 'warning',
        message: `High risk level in ${highRiskCount} provinces`,
        icon: ExclamationTriangleIcon,
        color: 'text-red-600 bg-red-50 border-red-200'
      };
    }

    const moderateRiskCount = alertSummary
      .filter(alert => alert.level === 'moderate')
      .reduce((sum, alert) => sum + alert.count, 0);

    if (moderateRiskCount > 0) {
      return {
        status: 'info',
        message: `Moderate risk level in ${moderateRiskCount} provinces`,
        icon: InformationCircleIcon,
        color: 'text-yellow-600 bg-yellow-50 border-yellow-200'
      };
    }

    return {
      status: 'success',
      message: 'Air quality is good in all provinces',
      icon: CheckCircleIcon,
      color: 'text-green-600 bg-green-50 border-green-200'
    };
  };

  const overallStatus = getOverallStatus();
  const StatusIcon = overallStatus.icon;

  return (
    <section className="py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Overall Status */}
        <div className={`rounded-lg border p-6 mb-8 ${overallStatus.color}`}>
          <div className="flex items-center">
            <StatusIcon className="h-8 w-8 mr-4" />
            <div>
              <h2 className="text-xl font-bold mb-1">Current Status</h2>
              <p className="text-lg">{overallStatus.message}</p>
              <p className="text-sm opacity-75 mt-1">
                Last updated: {new Date().toLocaleString('en-US')}
              </p>
            </div>
          </div>
        </div>

        {/* Alert Level Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          {alertSummary.map((alert) => (
            <div 
              key={alert.level}
              className="bg-white rounded-lg border shadow-sm p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-2">
                <div 
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: alert.color }}
                />
                <span className="text-2xl font-bold text-gray-900">
                  {alert.count}
                </span>
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">
                {alert.label}
              </h3>
              <p className="text-sm text-gray-600">
                {alert.count === 1 ? '1 province' : `${alert.count} provinces`}
              </p>
            </div>
          ))}
        </div>

        {/* Detailed Alert List */}
        <div className="space-y-4">
          {alertSummary
            .filter(alert => alert.level !== 'none') // Only show alerts, not normal levels
            .map((alert) => (
              <div key={alert.level} className="bg-white rounded-lg border shadow-sm">
                <button
                  onClick={() => setExpandedLevel(
                    expandedLevel === alert.level ? null : alert.level
                  )}
                  className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center">
                    <div 
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: alert.color }}
                    />
                    <div className="text-left">
                      <h3 className="font-semibold text-gray-900">
                        {alert.label} - {alert.count} Provinces
                      </h3>
                      <p className="text-sm text-gray-600">
                        {alert.provinces.map(p => p.province.name).join(', ')}
                      </p>
                    </div>
                  </div>
                  {expandedLevel === alert.level ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                  )}
                </button>

                {expandedLevel === alert.level && (
                  <div className="border-t border-gray-200 p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {alert.provinces.map(({ province, stats }) => (
                        <div 
                          key={province.id}
                          className="border rounded-lg p-3 hover:bg-gray-50"
                        >
                          <h4 className="font-semibold text-gray-900 mb-2">
                            {province.name}
                          </h4>
                          
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">PM2.5:</span>
                              <span className="font-medium">
                                {dataUtils.formatPM25(stats.pm25 || 0)}
                              </span>
                            </div>
                            
                            <div className="flex justify-between">
                              <span className="text-gray-600">Air Quality:</span>
                              <span className="font-medium">
                                {stats.pm25 ? dataUtils.getAirQualityCategory(stats.pm25) : 'N/A'}
                              </span>
                            </div>
                            
                            {stats.dust_event_detected && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">Dust:</span>
                                <span className="font-medium text-orange-600">
                                  {stats.dust_intensity || 'Detected'}
                                </span>
                              </div>
                            )}
                            
                            <div className="flex justify-between">
                              <span className="text-gray-600">AOD:</span>
                              <span className="font-medium">
                                {dataUtils.formatAOD(stats.aod_mean || 0)}
                              </span>
                            </div>
                          </div>

                          {/* Health recommendations */}
                          <div className="mt-3 pt-2 border-t border-gray-200">
                            <p className="text-xs text-gray-600 mb-1">Health Advice:</p>
                            <div className="text-xs text-gray-800">
                              {dataUtils.getHealthRecommendations(alert.level, 'general')[0]}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* General health advice for this alert level */}
                    <div className="mt-4 p-3 bg-gray-50 rounded-md">
                      <h4 className="font-semibold text-sm text-gray-900 mb-2">
                        General Recommendations ({alert.label}):
                      </h4>
                      <ul className="text-sm text-gray-700 space-y-1">
                        {dataUtils.getHealthRecommendations(alert.level, 'general').map((rec, index) => (
                          <li key={index} className="flex items-start">
                            <span className="mr-2">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* No alerts message */}
        {alertSummary.filter(alert => alert.level !== 'none').length === 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
            <CheckCircleIcon className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-green-900 mb-2">
              Great News! 🎉
            </h3>
            <p className="text-green-700">
              There is currently no air quality issue at alert levels in any province. 
              Air quality is at normal levels across all provinces.
            </p>
          </div>
        )}

        {/* Information box */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-start">
            <InformationCircleIcon className="h-6 w-6 text-blue-600 mr-3 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900 mb-2">
                About the Alert System
              </h3>
              <div className="text-sm text-blue-800 space-y-2">
                <p>
                  These alerts are calculated using NASA MODIS satellite data and ECMWF CAMS dust forecast models.
                </p>
                <p>
                  To receive personalized alerts{' '}
                  <a href="/register" className="font-semibold underline hover:text-blue-900">
                    sign up for free
                  </a>.
                </p>
                <p>
                  Data is updated daily and provides forecasts 48-72 hours in advance.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AlertsOverview;
