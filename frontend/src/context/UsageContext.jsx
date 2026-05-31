import React, { createContext, useContext, useEffect, useState } from "react";

const UsageContext = createContext(null);

export const UsageProvider = ({ children }) => {
  const [usageData, setUsageData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchUsage = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/usage-limits/summary", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setUsageData(data.counters);
      }
    } catch (error) {
      console.error("Failed to fetch usage data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, []);

  const getUsage = (usageKey) => {
    return usageData ? usageData[usageKey] : null;
  };

  const isLimitReached = (usageKey) => {
    const data = getUsage(usageKey);
    return data ? data.blocked : false;
  };

  const isNearLimit = (usageKey) => {
    const data = getUsage(usageKey);
    return data ? data.warning : false;
  };

  const getRemaining = (usageKey) => {
    const data = getUsage(usageKey);
    return data ? data.remaining : null;
  };

  const getUsageMessage = (usageKey) => {
    const data = getUsage(usageKey);
    return data ? data.message : null;
  };

  return (
    <UsageContext.Provider
      value={{
        usageData,
        loading,
        fetchUsage,
        getUsage,
        isLimitReached,
        isNearLimit,
        getRemaining,
        getUsageMessage,
      }}
    >
      {children}
    </UsageContext.Provider>
  );
};

export const useUsage = () => {
  const context = useContext(UsageContext);
  if (!context) {
    throw new Error("useUsage must be used within a UsageProvider");
  }
  return context;
};
