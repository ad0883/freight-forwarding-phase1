import React from 'react';

export function Card({ className = "", children, ...props }) {
  return (
    <div className={`billing-card ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...props }) {
  return (
    <div className={`billing-card-header ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className = "", children, ...props }) {
  return (
    <h3 className={`billing-card-title ${className}`.trim()} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ className = "", children, ...props }) {
  return (
    <div className={`billing-card-content ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}
