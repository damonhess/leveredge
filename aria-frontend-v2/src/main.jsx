import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import { ThemeProvider } from './hooks/useTheme';
import { ThemeSegmentedControl } from './components/ThemeToggle';
import './styles/globals.css';

// Import examples
import { ChartExample } from '../examples/ChartExample';
import { TableExample } from '../examples/TableExample';
import { CodeExample } from '../examples/CodeExample';

const examples = {
  charts: { name: 'Charts', component: ChartExample },
  tables: { name: 'Tables', component: TableExample },
  code: { name: 'Code & Diagrams', component: CodeExample },
};

function App() {
  const [activeExample, setActiveExample] = useState('charts');
  const ActiveComponent = examples[activeExample].component;

  return (
    <ThemeProvider defaultTheme="system">
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Navigation */}
        <nav className="sticky top-0 z-50 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  ARIA Frontend V2
                </h1>
                <div className="flex gap-1">
                  {Object.entries(examples).map(([key, { name }]) => (
                    <button
                      key={key}
                      onClick={() => setActiveExample(key)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
                        ${activeExample === key
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
              <ThemeSegmentedControl />
            </div>
          </div>
        </nav>

        {/* Content */}
        <main>
          <ActiveComponent />
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 dark:border-gray-700 py-6 mt-12">
          <div className="max-w-6xl mx-auto px-4 text-center text-gray-500 dark:text-gray-400 text-sm">
            ARIA Frontend V2 - Component Library for ARIA AI Assistant
          </div>
        </footer>
      </div>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
