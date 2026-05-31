import React from 'react';
import { useUsage } from '../context/UsageContext';

export default function UsageLimitsPage() {
  const { usageData, loading, fetchUsage } = useUsage();

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        Loading usage data...
      </div>
    );
  }

  if (!usageData) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        No usage data available.
      </div>
    );
  }

  const formatPercentage = (current, limit) => {
    if (limit === null) return 0;
    const p = (current / limit) * 100;
    return p > 100 ? 100 : p;
  };

  const getBarColor = (item) => {
    if (item.blocked) return 'bg-red-500';
    if (item.warning) return 'bg-yellow-500';
    return 'bg-blue-600';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Subscription & Usage Limits</h1>
        <button
          onClick={fetchUsage}
          className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          Refresh Data
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(usageData).map(([key, item]) => {
          const percentage = formatPercentage(item.current, item.limit);
          const limitText = item.limit === null ? 'Unlimited' : item.limit;
          
          return (
            <div key={key} className="overflow-hidden rounded-lg bg-white shadow ring-1 ring-black/5">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="w-0 flex-1">
                    <dl>
                      <dt className="truncate text-sm font-medium text-gray-500 capitalize">
                        {key.replace(/_/g, ' ')}
                      </dt>
                      <dd>
                        <div className="text-lg font-medium text-gray-900">
                          {item.current} <span className="text-sm text-gray-500 font-normal">/ {limitText}</span>
                        </div>
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-5 py-3">
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                  <div 
                    className={`h-2.5 rounded-full ${getBarColor(item)}`} 
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
                <div className="text-sm">
                  {item.blocked ? (
                    <span className="text-red-600 font-medium">{item.message || 'Limit reached'}</span>
                  ) : item.warning ? (
                    <span className="text-yellow-600 font-medium">{item.message || 'Approaching limit'}</span>
                  ) : (
                    <span className="text-gray-500">
                      {item.limit === null ? 'No limit' : `${item.remaining} remaining`}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
