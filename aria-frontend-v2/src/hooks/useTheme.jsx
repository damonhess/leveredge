import { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react';

// Theme context for provider pattern
const ThemeContext = createContext(null);

// Storage key
const THEME_STORAGE_KEY = 'aria-theme';

// Available themes
const THEMES = ['light', 'dark', 'system'];

/**
 * Get system preference for color scheme
 */
function getSystemTheme() {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Get stored theme from localStorage
 */
function getStoredTheme() {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    return THEMES.includes(stored) ? stored : null;
  } catch {
    return null;
  }
}

/**
 * Apply theme to document
 */
function applyTheme(theme) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;

  // Update class on html element
  root.classList.remove('light', 'dark');
  root.classList.add(resolvedTheme);

  // Update color-scheme for native elements
  root.style.colorScheme = resolvedTheme;

  // Update meta theme-color
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.content = resolvedTheme === 'dark' ? '#111827' : '#ffffff';
  }
}

/**
 * useTheme Hook - Theme management with persistence
 *
 * @param {Object} options
 * @param {string} options.defaultTheme - Default theme ('light' | 'dark' | 'system')
 * @param {string} options.storageKey - localStorage key for persistence
 * @returns {Object} Theme state and controls
 */
export function useTheme(options = {}) {
  const {
    defaultTheme = 'system',
    storageKey = THEME_STORAGE_KEY,
  } = options;

  // Initialize theme from storage or default
  const [theme, setThemeState] = useState(() => {
    const stored = getStoredTheme();
    return stored || defaultTheme;
  });

  // Resolved theme (actual light/dark value)
  const [resolvedTheme, setResolvedTheme] = useState(() => {
    const currentTheme = getStoredTheme() || defaultTheme;
    return currentTheme === 'system' ? getSystemTheme() : currentTheme;
  });

  // Set theme with persistence
  const setTheme = useCallback((newTheme) => {
    if (!THEMES.includes(newTheme)) {
      console.warn(`Invalid theme: ${newTheme}. Use 'light', 'dark', or 'system'.`);
      return;
    }

    setThemeState(newTheme);

    // Persist to localStorage
    try {
      localStorage.setItem(storageKey, newTheme);
    } catch (err) {
      console.warn('Failed to persist theme:', err);
    }

    // Apply theme
    applyTheme(newTheme);
    setResolvedTheme(newTheme === 'system' ? getSystemTheme() : newTheme);
  }, [storageKey]);

  // Toggle between light and dark
  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  // Apply theme on mount and listen for system preference changes
  useEffect(() => {
    // Apply initial theme
    applyTheme(theme);

    // Listen for system preference changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e) => {
      if (theme === 'system') {
        const newResolvedTheme = e.matches ? 'dark' : 'light';
        setResolvedTheme(newResolvedTheme);
        applyTheme('system');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // Listen for storage changes (cross-tab sync)
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === storageKey && e.newValue && THEMES.includes(e.newValue)) {
        setThemeState(e.newValue);
        applyTheme(e.newValue);
        setResolvedTheme(e.newValue === 'system' ? getSystemTheme() : e.newValue);
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [storageKey]);

  return useMemo(() => ({
    theme,           // Current theme setting ('light' | 'dark' | 'system')
    resolvedTheme,   // Actual resolved theme ('light' | 'dark')
    setTheme,        // Set theme function
    toggleTheme,     // Toggle between light/dark
    themes: THEMES,  // Available themes
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
    isSystem: theme === 'system',
  }), [theme, resolvedTheme, setTheme, toggleTheme]);
}

/**
 * ThemeProvider Component - Provides theme context to children
 */
export function ThemeProvider({ children, defaultTheme = 'system' }) {
  const themeValue = useTheme({ defaultTheme });

  return (
    <ThemeContext.Provider value={themeValue}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * useThemeContext - Use theme from context (requires ThemeProvider)
 */
export function useThemeContext() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }
  return context;
}

/**
 * Script to prevent flash of incorrect theme
 * Include this in <head> before other scripts
 */
export const themeScript = `
(function() {
  try {
    var theme = localStorage.getItem('${THEME_STORAGE_KEY}');
    var resolved = theme === 'system' || !theme
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      : theme;
    document.documentElement.classList.add(resolved);
    document.documentElement.style.colorScheme = resolved;
  } catch (e) {}
})();
`;

export default useTheme;
