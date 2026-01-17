import React, { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import clsx from 'clsx';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassPlusIcon,
  MagnifyingGlassMinusIcon,
  ArrowsPointingOutIcon,
  ArrowDownTrayIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

/**
 * PDFViewer Component - PDF viewer with page navigation
 *
 * @param {Object} props
 * @param {string} props.src - PDF file URL or base64 data
 * @param {string} props.title - Document title
 * @param {number} props.initialPage - Initial page number
 * @param {number} props.initialScale - Initial zoom scale
 * @param {boolean} props.showControls - Show navigation controls
 * @param {boolean} props.showDownload - Show download button
 * @param {boolean} props.showPageNumbers - Show page numbers
 * @param {string} props.className - Additional CSS classes
 */
export function PDFViewer({
  src,
  title,
  initialPage = 1,
  initialScale = 1,
  showControls = true,
  showDownload = true,
  showPageNumbers = true,
  className,
  width = 'auto',
  height,
  onLoadSuccess,
  onLoadError,
}) {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [scale, setScale] = useState(initialScale);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleDocumentLoadSuccess = useCallback(({ numPages: total }) => {
    setNumPages(total);
    setIsLoading(false);
    onLoadSuccess?.({ numPages: total });
  }, [onLoadSuccess]);

  const handleDocumentLoadError = useCallback((err) => {
    setError('Failed to load PDF');
    setIsLoading(false);
    console.error('PDF load error:', err);
    onLoadError?.(err);
  }, [onLoadError]);

  const goToPrevPage = useCallback(() => {
    setPageNumber((prev) => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setPageNumber((prev) => Math.min(numPages || prev, prev + 1));
  }, [numPages]);

  const goToPage = useCallback((page) => {
    const pageNum = parseInt(page, 10);
    if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= numPages) {
      setPageNumber(pageNum);
    }
  }, [numPages]);

  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(3, prev + 0.25));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.5, prev - 0.25));
  }, []);

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  const handleDownload = useCallback(() => {
    if (src) {
      const link = document.createElement('a');
      link.href = src;
      link.download = title || 'document.pdf';
      link.click();
    }
  }, [src, title]);

  // Keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowLeft') goToPrevPage();
      if (e.key === 'ArrowRight') goToNextPage();
      if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goToPrevPage, goToNextPage, isFullscreen]);

  if (!src) {
    return (
      <div className={clsx('aria-pdf-viewer', className)}>
        <div className="flex flex-col items-center justify-center p-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
          <DocumentIcon className="w-12 h-12 text-gray-400 dark:text-gray-500 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No PDF document provided</p>
        </div>
      </div>
    );
  }

  const viewerContent = (
    <div className={clsx(
      'aria-pdf-viewer bg-gray-100 dark:bg-gray-900 rounded-lg overflow-hidden',
      isFullscreen && 'fixed inset-0 z-50',
      className
    )}>
      {/* Header/Controls */}
      {showControls && (
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            {title && (
              <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]">
                {title}
              </h4>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Page navigation */}
            <div className="flex items-center gap-1">
              <button
                onClick={goToPrevPage}
                disabled={pageNumber <= 1}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                           disabled:opacity-50 disabled:cursor-not-allowed
                           text-gray-600 dark:text-gray-400"
                title="Previous page"
              >
                <ChevronLeftIcon className="w-5 h-5" />
              </button>

              {showPageNumbers && (
                <div className="flex items-center gap-1 text-sm">
                  <input
                    type="number"
                    min={1}
                    max={numPages || 1}
                    value={pageNumber}
                    onChange={(e) => goToPage(e.target.value)}
                    className="w-12 px-2 py-1 text-center border border-gray-300 dark:border-gray-600
                               rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <span className="text-gray-500 dark:text-gray-400">
                    / {numPages || '-'}
                  </span>
                </div>
              )}

              <button
                onClick={goToNextPage}
                disabled={pageNumber >= (numPages || 1)}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                           disabled:opacity-50 disabled:cursor-not-allowed
                           text-gray-600 dark:text-gray-400"
                title="Next page"
              >
                <ChevronRightIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-2" />

            {/* Zoom controls */}
            <div className="flex items-center gap-1">
              <button
                onClick={zoomOut}
                disabled={scale <= 0.5}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                           disabled:opacity-50 disabled:cursor-not-allowed
                           text-gray-600 dark:text-gray-400"
                title="Zoom out"
              >
                <MagnifyingGlassMinusIcon className="w-5 h-5" />
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400 w-12 text-center">
                {Math.round(scale * 100)}%
              </span>
              <button
                onClick={zoomIn}
                disabled={scale >= 3}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                           disabled:opacity-50 disabled:cursor-not-allowed
                           text-gray-600 dark:text-gray-400"
                title="Zoom in"
              >
                <MagnifyingGlassPlusIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="w-px h-6 bg-gray-300 dark:bg-gray-600 mx-2" />

            {/* Actions */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                         text-gray-600 dark:text-gray-400"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              <ArrowsPointingOutIcon className="w-5 h-5" />
            </button>

            {showDownload && (
              <button
                onClick={handleDownload}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                           text-gray-600 dark:text-gray-400"
                title="Download PDF"
              >
                <ArrowDownTrayIcon className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* PDF Document */}
      <div
        className={clsx(
          'overflow-auto',
          isFullscreen ? 'h-[calc(100vh-52px)]' : ''
        )}
        style={{ height: !isFullscreen && height ? `${height}px` : undefined }}
      >
        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            <span className="ml-3 text-gray-600 dark:text-gray-400">Loading PDF...</span>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="flex flex-col items-center justify-center p-12">
            <DocumentIcon className="w-12 h-12 text-red-400 mb-3" />
            <p className="text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* PDF content */}
        <Document
          file={src}
          onLoadSuccess={handleDocumentLoadSuccess}
          onLoadError={handleDocumentLoadError}
          loading=""
          className="flex flex-col items-center py-4"
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            width={width !== 'auto' ? width : undefined}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            className="shadow-lg"
          />
        </Document>
      </div>
    </div>
  );

  return viewerContent;
}

/**
 * PDFThumbnails Component - Show PDF page thumbnails
 */
export function PDFThumbnails({
  src,
  onPageSelect,
  selectedPage = 1,
  className,
}) {
  const [numPages, setNumPages] = useState(null);

  const handleLoadSuccess = ({ numPages: total }) => {
    setNumPages(total);
  };

  return (
    <div className={clsx('aria-pdf-thumbnails', className)}>
      <Document
        file={src}
        onLoadSuccess={handleLoadSuccess}
        className="flex flex-wrap gap-2"
      >
        {numPages && Array.from({ length: numPages }, (_, i) => i + 1).map((page) => (
          <button
            key={page}
            onClick={() => onPageSelect?.(page)}
            className={clsx(
              'border-2 rounded overflow-hidden transition-colors',
              selectedPage === page
                ? 'border-blue-500'
                : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
            )}
          >
            <Page
              pageNumber={page}
              width={100}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
            <div className="text-xs text-center py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
              {page}
            </div>
          </button>
        ))}
      </Document>
    </div>
  );
}

export default PDFViewer;
