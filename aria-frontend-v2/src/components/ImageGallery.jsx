import React, { useState, useCallback } from 'react';
import Lightbox from 'yet-another-react-lightbox';
import 'yet-another-react-lightbox/styles.css';
import clsx from 'clsx';
import {
  PhotoIcon,
  ArrowsPointingOutIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

/**
 * ImageGallery Component - Image gallery with lightbox
 *
 * @param {Object} props
 * @param {Array} props.images - Array of image objects { src, alt, title, thumbnail }
 * @param {number} props.columns - Number of columns in grid (1-6)
 * @param {string} props.gap - Gap between images ('sm' | 'md' | 'lg')
 * @param {boolean} props.showCaptions - Show image captions
 * @param {string} props.aspectRatio - Image aspect ratio ('square' | '4:3' | '16:9' | 'auto')
 * @param {string} props.className - Additional CSS classes
 */
export function ImageGallery({
  images = [],
  columns = 3,
  gap = 'md',
  showCaptions = false,
  aspectRatio = 'square',
  className,
  title,
}) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  const openLightbox = useCallback((index) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
  }, []);

  const gapClasses = {
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };

  const columnClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5',
    6: 'grid-cols-2 sm:grid-cols-4 lg:grid-cols-6',
  };

  const aspectClasses = {
    square: 'aspect-square',
    '4:3': 'aspect-[4/3]',
    '16:9': 'aspect-video',
    auto: '',
  };

  // Convert images to lightbox format
  const lightboxSlides = images.map((img) => ({
    src: img.src,
    alt: img.alt || '',
    title: img.title,
  }));

  if (images.length === 0) {
    return (
      <div className={clsx('aria-image-gallery', className)}>
        <div className="flex flex-col items-center justify-center p-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-dashed border-gray-300 dark:border-gray-600">
          <PhotoIcon className="w-12 h-12 text-gray-400 dark:text-gray-500 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No images to display</p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('aria-image-gallery', className)}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {title}
        </h3>
      )}

      {/* Image Grid */}
      <div className={clsx('grid', columnClasses[columns] || columnClasses[3], gapClasses[gap])}>
        {images.map((image, index) => (
          <div
            key={index}
            className="group relative overflow-hidden rounded-lg bg-gray-100 dark:bg-gray-800 cursor-pointer"
            onClick={() => openLightbox(index)}
          >
            <div className={clsx(aspectClasses[aspectRatio])}>
              <img
                src={image.thumbnail || image.src}
                alt={image.alt || `Image ${index + 1}`}
                className={clsx(
                  'w-full h-full object-cover transition-transform duration-300',
                  'group-hover:scale-105'
                )}
                loading="lazy"
              />
            </div>

            {/* Hover overlay */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors duration-300 flex items-center justify-center">
              <ArrowsPointingOutIcon className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>

            {/* Caption */}
            {showCaptions && image.title && (
              <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/70 to-transparent">
                <p className="text-sm text-white truncate">{image.title}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      <Lightbox
        open={lightboxOpen}
        close={() => setLightboxOpen(false)}
        index={currentIndex}
        slides={lightboxSlides}
        carousel={{ finite: images.length <= 1 }}
        render={{
          iconPrev: () => <ChevronLeftIcon className="w-8 h-8" />,
          iconNext: () => <ChevronRightIcon className="w-8 h-8" />,
          iconClose: () => <XMarkIcon className="w-8 h-8" />,
        }}
        styles={{
          container: { backgroundColor: 'rgba(0, 0, 0, 0.9)' },
        }}
      />
    </div>
  );
}

/**
 * SingleImage Component - Display a single image with optional lightbox
 */
export function SingleImage({
  src,
  alt,
  title,
  caption,
  className,
  zoomable = true,
  rounded = true,
}) {
  const [isZoomed, setIsZoomed] = useState(false);

  return (
    <div className={clsx('aria-single-image', className)}>
      {title && (
        <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {title}
        </h4>
      )}

      <figure className="relative">
        <div
          className={clsx(
            'relative overflow-hidden bg-gray-100 dark:bg-gray-800',
            rounded && 'rounded-lg',
            zoomable && 'cursor-pointer group'
          )}
          onClick={() => zoomable && setIsZoomed(true)}
        >
          <img
            src={src}
            alt={alt || title || 'Image'}
            className="w-full h-auto object-contain"
          />
          {zoomable && (
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300 flex items-center justify-center">
              <ArrowsPointingOutIcon className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
          )}
        </div>

        {caption && (
          <figcaption className="mt-2 text-sm text-gray-600 dark:text-gray-400 text-center">
            {caption}
          </figcaption>
        )}
      </figure>

      {/* Zoom modal */}
      {isZoomed && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={() => setIsZoomed(false)}
        >
          <button
            className="absolute top-4 right-4 p-2 text-white hover:bg-white/20 rounded-full transition-colors"
            onClick={() => setIsZoomed(false)}
          >
            <XMarkIcon className="w-8 h-8" />
          </button>
          <img
            src={src}
            alt={alt || title || 'Image'}
            className="max-w-[90vw] max-h-[90vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}

export default ImageGallery;
