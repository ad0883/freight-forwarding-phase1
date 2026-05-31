import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './styles/global.css';

import { FeatureProvider } from './context/FeatureContext.jsx';

import { UsageProvider } from './context/UsageContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <FeatureProvider>
      <UsageProvider>
        <App />
      </UsageProvider>
    </FeatureProvider>
  </BrowserRouter>
);
