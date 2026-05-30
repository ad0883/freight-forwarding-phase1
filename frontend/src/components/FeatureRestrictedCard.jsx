import React from 'react';
import { Shield } from 'lucide-react';
import { useFeatures } from '../context/FeatureContext';
import { FEATURE_NAMES } from '../config/features';

export default function FeatureRestrictedCard({ featureKey, title = "Upgrade Required" }) {
  const { planKey } = useFeatures();
  const featureName = FEATURE_NAMES[featureKey] || "this feature";
  
  return (
    <div className="page-stack">
      <section className="panel permission-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <Shield size={48} style={{ margin: '0 auto 1.5rem', color: 'var(--text-muted)' }} />
        <h1>{title}</h1>
        <p className="muted" style={{ maxWidth: '400px', margin: '1rem auto' }}>
          Your current <strong style={{textTransform: 'capitalize'}}>{planKey || 'Starter'}</strong> plan does not include access to {featureName}.
        </p>
        <p className="muted" style={{ maxWidth: '400px', margin: '0 auto' }}>
          Please contact your organization administrator to upgrade your subscription.
        </p>
      </section>
    </div>
  );
}
