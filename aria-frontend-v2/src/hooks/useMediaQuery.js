import { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * useMediaQuery Hook - Responsive breakpoint detection
 *
 * @param {string} query - Media query string (e.g., '(min-width: 768px)')
 * @returns {boolean} Whether the media query matches
 */
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);

    // Update state when query matches change
    const handleChange = (e) => {
      setMatches(e.matches);
    };

    // Set initial value
    setMatches(mediaQuery.matches);

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [query]);

  return matches;
}

// Pre-defined breakpoints (matching Tailwind defaults)
const BREAKPOINTS = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

/**
 * useBreakpoint Hook - Check if viewport is at or above a breakpoint
 *
 * @param {string} breakpoint - Breakpoint name ('sm' | 'md' | 'lg' | 'xl' | '2xl')
 * @returns {boolean} Whether viewport is at or above the breakpoint
 */
export function useBreakpoint(breakpoint) {
  const width = BREAKPOINTS[breakpoint];
  if (!width) {
    console.warn(`Invalid breakpoint: ${breakpoint}. Use: sm, md, lg, xl, or 2xl`);
    return false;
  }
  return useMediaQuery(`(min-width: ${width})`);
}

/**
 * useBreakpoints Hook - Get current breakpoint info
 *
 * @returns {Object} Breakpoint information
 */
export function useBreakpoints() {
  const isSm = useBreakpoint('sm');
  const isMd = useBreakpoint('md');
  const isLg = useBreakpoint('lg');
  const isXl = useBreakpoint('xl');
  const is2xl = useBreakpoint('2xl');

  return useMemo(() => {
    // Determine current breakpoint
    let current = 'xs';
    if (is2xl) current = '2xl';
    else if (isXl) current = 'xl';
    else if (isLg) current = 'lg';
    else if (isMd) current = 'md';
    else if (isSm) current = 'sm';

    return {
      // Current breakpoint name
      current,
      // Boolean flags for each breakpoint
      isSm,
      isMd,
      isLg,
      isXl,
      is2xl,
      // Convenience flags
      isMobile: !isMd,
      isTablet: isMd && !isLg,
      isDesktop: isLg,
      // Helper for conditional values
      breakpoint: (values) => {
        if (is2xl && values['2xl'] !== undefined) return values['2xl'];
        if (isXl && values.xl !== undefined) return values.xl;
        if (isLg && values.lg !== undefined) return values.lg;
        if (isMd && values.md !== undefined) return values.md;
        if (isSm && values.sm !== undefined) return values.sm;
        return values.xs !== undefined ? values.xs : values.default;
      },
    };
  }, [isSm, isMd, isLg, isXl, is2xl]);
}

/**
 * useIsMobile Hook - Simple mobile detection
 */
export function useIsMobile() {
  return !useBreakpoint('md');
}

/**
 * useIsDesktop Hook - Simple desktop detection
 */
export function useIsDesktop() {
  return useBreakpoint('lg');
}

/**
 * usePrefersReducedMotion Hook - Detect reduced motion preference
 */
export function usePrefersReducedMotion() {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * usePrefersDarkMode Hook - Detect system dark mode preference
 */
export function usePrefersDarkMode() {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * usePrefersHighContrast Hook - Detect high contrast preference
 */
export function usePrefersHighContrast() {
  return useMediaQuery('(prefers-contrast: more)');
}

/**
 * useOrientation Hook - Detect device orientation
 */
export function useOrientation() {
  const isPortrait = useMediaQuery('(orientation: portrait)');
  return isPortrait ? 'portrait' : 'landscape';
}

/**
 * useWindowSize Hook - Get window dimensions
 */
export function useWindowSize() {
  const [size, setSize] = useState(() => {
    if (typeof window === 'undefined') {
      return { width: 0, height: 0 };
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight,
    };
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    // Debounced resize handler
    let timeoutId;
    const debouncedResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(handleResize, 100);
    };

    window.addEventListener('resize', debouncedResize);
    return () => {
      window.removeEventListener('resize', debouncedResize);
      clearTimeout(timeoutId);
    };
  }, []);

  return size;
}

/**
 * useContainerQuery Hook - Container query-like behavior (width-based)
 * Note: For actual CSS container queries, use CSS directly
 *
 * @param {React.RefObject} ref - Reference to the container element
 * @param {Object} breakpoints - Custom breakpoints { name: width }
 */
export function useContainerQuery(ref, breakpoints = BREAKPOINTS) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    if (!ref.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);

  return useMemo(() => {
    const result = { width };

    // Add boolean flags for each breakpoint
    for (const [name, minWidth] of Object.entries(breakpoints)) {
      const breakpointWidth = parseInt(minWidth, 10);
      result[`is${name.charAt(0).toUpperCase()}${name.slice(1)}`] = width >= breakpointWidth;
    }

    return result;
  }, [width, breakpoints]);
}

export default useMediaQuery;
