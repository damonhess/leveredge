import React, { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';
import clsx from 'clsx';
import { ArrowsPointingOutIcon, ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

// Configure mermaid defaults
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis',
  },
  sequence: {
    useMaxWidth: true,
    diagramMarginX: 50,
    diagramMarginY: 10,
  },
  gantt: {
    useMaxWidth: true,
  },
});

/**
 * MermaidDiagram Component - Renders Mermaid diagrams
 *
 * @param {Object} props
 * @param {string} props.chart - Mermaid diagram definition
 * @param {string} props.title - Optional diagram title
 * @param {string} props.theme - 'default' | 'dark' | 'forest' | 'neutral'
 * @param {boolean} props.zoomable - Enable zoom on click
 * @param {string} props.className - Additional CSS classes
 */
export function MermaidDiagram({
  chart = '',
  title,
  theme: themeOverride,
  zoomable = true,
  className,
  onError,
}) {
  const containerRef = useRef(null);
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);
  const [isZoomed, setIsZoomed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const renderDiagram = useCallback(async () => {
    if (!chart || !containerRef.current) return;

    setIsLoading(true);
    setError(null);

    try {
      // Determine theme
      let effectiveTheme = themeOverride;
      if (!effectiveTheme) {
        const isDark = typeof document !== 'undefined' &&
          document.documentElement.classList.contains('dark');
        effectiveTheme = isDark ? 'dark' : 'default';
      }

      // Update mermaid config
      mermaid.initialize({
        startOnLoad: false,
        theme: effectiveTheme,
        securityLevel: 'loose',
      });

      // Generate unique ID
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      // Render the diagram
      const { svg: renderedSvg } = await mermaid.render(id, chart);
      setSvg(renderedSvg);
    } catch (err) {
      console.error('Mermaid render error:', err);
      setError(err.message || 'Failed to render diagram');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  }, [chart, themeOverride, onError]);

  useEffect(() => {
    renderDiagram();
  }, [renderDiagram]);

  // Listen for theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          renderDiagram();
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, [renderDiagram]);

  const handleZoomToggle = () => {
    setIsZoomed(!isZoomed);
  };

  const handleRetry = () => {
    renderDiagram();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={clsx('aria-mermaid-diagram', className)}>
        <div className="flex items-center justify-center p-8 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">Rendering diagram...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={clsx('aria-mermaid-diagram', className)}>
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="flex items-start gap-3">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 dark:text-red-400">
                Diagram Render Error
              </h4>
              <p className="mt-1 text-sm text-red-600 dark:text-red-300">{error}</p>
              <button
                onClick={handleRetry}
                className="mt-2 flex items-center gap-1 text-sm text-red-600 dark:text-red-400 hover:underline"
              >
                <ArrowPathIcon className="w-4 h-4" />
                Retry
              </button>
            </div>
          </div>
          {/* Show raw chart for debugging */}
          <details className="mt-3">
            <summary className="text-xs text-red-500 cursor-pointer">Show raw definition</summary>
            <pre className="mt-2 p-2 bg-white dark:bg-gray-900 rounded text-xs overflow-x-auto">
              {chart}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={clsx('aria-mermaid-diagram', className)} ref={containerRef}>
        {title && (
          <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 text-center">
            {title}
          </h4>
        )}
        <div className="relative bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 overflow-x-auto">
          {zoomable && (
            <button
              onClick={handleZoomToggle}
              className="absolute top-2 right-2 p-1.5 rounded bg-gray-100 dark:bg-gray-800
                         hover:bg-gray-200 dark:hover:bg-gray-700
                         text-gray-600 dark:text-gray-400
                         transition-colors duration-150 z-10"
              title="Toggle fullscreen"
            >
              <ArrowsPointingOutIcon className="w-4 h-4" />
            </button>
          )}
          <div
            className="flex justify-center [&>svg]:max-w-full"
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      </div>

      {/* Zoom modal */}
      {isZoomed && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-8"
          onClick={handleZoomToggle}
        >
          <div
            className="max-w-[90vw] max-h-[90vh] overflow-auto bg-white dark:bg-gray-900 rounded-lg p-6"
            onClick={(e) => e.stopPropagation()}
          >
            {title && (
              <h4 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4 text-center">
                {title}
              </h4>
            )}
            <div
              className="[&>svg]:max-w-full"
              dangerouslySetInnerHTML={{ __html: svg }}
            />
          </div>
        </div>
      )}
    </>
  );
}

// Pre-defined diagram type helpers
export const FlowchartDiagram = ({ definition, ...props }) => (
  <MermaidDiagram chart={`flowchart TD\n${definition}`} {...props} />
);

export const SequenceDiagram = ({ definition, ...props }) => (
  <MermaidDiagram chart={`sequenceDiagram\n${definition}`} {...props} />
);

export const ClassDiagram = ({ definition, ...props }) => (
  <MermaidDiagram chart={`classDiagram\n${definition}`} {...props} />
);

export const GanttChart = ({ definition, ...props }) => (
  <MermaidDiagram chart={`gantt\n${definition}`} {...props} />
);

export const PieChart = ({ definition, ...props }) => (
  <MermaidDiagram chart={`pie\n${definition}`} {...props} />
);

export const ERDiagram = ({ definition, ...props }) => (
  <MermaidDiagram chart={`erDiagram\n${definition}`} {...props} />
);

export default MermaidDiagram;
