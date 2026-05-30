import React, { createContext, useContext, useEffect, useState } from 'react';

const FeatureContext = createContext({
  features: {},
  loading: true,
  error: null,
  planKey: null,
  refreshFeatures: () => {},
});

export const useFeatures = () => useContext(FeatureContext);

export const FeatureProvider = ({ children }) => {
  const [features, setFeatures] = useState({});
  const [planKey, setPlanKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchFeatures = async () => {
    try {
      setLoading(true);
      setError(null);
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }
      
      const response = await fetch('http://127.0.0.1:8000/api/subscriptions/features', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch features');
      }
      
      const data = await response.json();
      setFeatures(data.features || {});
      setPlanKey(data.plan_key);
    } catch (err) {
      console.error("Feature fetch error:", err);
      setError(err);
      setFeatures({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeatures();
  }, []);

  return (
    <FeatureContext.Provider value={{ features, planKey, loading, error, refreshFeatures: fetchFeatures }}>
      {children}
    </FeatureContext.Provider>
  );
};
