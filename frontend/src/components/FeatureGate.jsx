import React from 'react';
import { useFeatures } from '../context/FeatureContext';
import { LoadingState } from './States';
import FeatureRestrictedCard from './FeatureRestrictedCard';

export default function FeatureGate({ featureKey, children }) {
  const { features, loading, error } = useFeatures();

  if (loading) {
    return <LoadingState label="Checking feature access..." />;
  }

  if (error) {
    // Fail safe to restricted if there's an error, or could show error state
    return <FeatureRestrictedCard featureKey={featureKey} title="Error checking access" />;
  }

  if (!features[featureKey]) {
    return <FeatureRestrictedCard featureKey={featureKey} />;
  }

  return children;
}
