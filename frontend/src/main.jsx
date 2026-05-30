import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import './styles/global.css';

import { FeatureProvider } from './context/FeatureContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <FeatureProvider>
      <App />
    </FeatureProvider>
  </BrowserRouter>
);
