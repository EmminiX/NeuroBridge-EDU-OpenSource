/**
 * Application Entry Point
 * 
 * Main entry point for the NeuroBridge EDU React application.
 * Sets up React 19 with proper error boundaries and providers.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

// Ensure we have a root element
const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

const root = createRoot(rootElement);

root.render(
  <StrictMode>
    <App />
  </StrictMode>
);