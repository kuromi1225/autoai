import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// エラーハンドリングを追加
window.addEventListener('error', (e) => {
  console.error('Global error:', e.error, e.filename, e.lineno, e.colno);
});

window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled promise rejection:', e.reason);
});

try {
  console.log('Starting React app...');
  const root = ReactDOM.createRoot(document.getElementById('root'))
  console.log('Root created, rendering...');
  root.render(<App />)
  console.log('App rendered successfully');
} catch (error) {
  console.error('Failed to render React app:', error);
  document.body.innerHTML = `
    <div style="padding: 20px; color: red; font-family: monospace;">
      <h1>React App Failed to Load</h1>
      <p>Error: ${error.message}</p>
      <pre>${error.stack}</pre>
    </div>
  `;
}
