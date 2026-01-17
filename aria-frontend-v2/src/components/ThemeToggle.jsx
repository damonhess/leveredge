import React from 'react';
import clsx from 'clsx';
import { SunIcon, MoonIcon, ComputerDesktopIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../hooks/useTheme';

/**
 * ThemeToggle Component - Dark/light mode toggle
 *
 * @param {Object} props
 * @param {string} props.variant - 'icon' | 'button' | 'switch' | 'dropdown'
 * @param {boolean} props.showLabel - Show text label
 * @param {boolean} props.showSystem - Show system theme option
 * @param {string} props.className - Additional CSS classes
 */
export function ThemeToggle({
  variant = 'icon',
  showLabel = false,
  showSystem = true,
  className,
}) {
  const { theme, setTheme, resolvedTheme, themes } = useTheme();

  const IconComponent = resolvedTheme === 'dark' ? MoonIcon : SunIcon;
  const label = resolvedTheme === 'dark' ? 'Dark' : 'Light';

  // Simple icon toggle
  if (variant === 'icon') {
    return (
      <button
        onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
        className={clsx(
          'p-2 rounded-lg transition-colors',
          'hover:bg-gray-100 dark:hover:bg-gray-800',
          'text-gray-600 dark:text-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
          'dark:focus:ring-offset-gray-900',
          className
        )}
        title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
        aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
      >
        <IconComponent className="w-5 h-5" />
        {showLabel && <span className="ml-2">{label}</span>}
      </button>
    );
  }

  // Button style toggle
  if (variant === 'button') {
    return (
      <button
        onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
        className={clsx(
          'inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
          'bg-gray-100 dark:bg-gray-800',
          'hover:bg-gray-200 dark:hover:bg-gray-700',
          'text-gray-700 dark:text-gray-300',
          'border border-gray-200 dark:border-gray-700',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          className
        )}
      >
        <IconComponent className="w-5 h-5" />
        <span>{label} Mode</span>
      </button>
    );
  }

  // Switch style toggle
  if (variant === 'switch') {
    const isDark = resolvedTheme === 'dark';

    return (
      <div className={clsx('flex items-center gap-3', className)}>
        <SunIcon className={clsx('w-5 h-5', isDark ? 'text-gray-500' : 'text-yellow-500')} />
        <button
          onClick={() => setTheme(isDark ? 'light' : 'dark')}
          className={clsx(
            'relative w-12 h-6 rounded-full transition-colors',
            isDark ? 'bg-blue-600' : 'bg-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            'dark:focus:ring-offset-gray-900'
          )}
          role="switch"
          aria-checked={isDark}
        >
          <span
            className={clsx(
              'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
              isDark ? 'translate-x-6' : 'translate-x-0.5'
            )}
          />
        </button>
        <MoonIcon className={clsx('w-5 h-5', isDark ? 'text-blue-400' : 'text-gray-500')} />
      </div>
    );
  }

  // Dropdown style with system option
  if (variant === 'dropdown') {
    return (
      <div className={clsx('relative', className)}>
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className={clsx(
            'appearance-none pl-10 pr-8 py-2 rounded-lg',
            'bg-white dark:bg-gray-800',
            'border border-gray-200 dark:border-gray-700',
            'text-gray-700 dark:text-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-blue-500',
            'cursor-pointer'
          )}
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          {showSystem && <option value="system">System</option>}
        </select>
        <IconComponent className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 pointer-events-none" />
        <svg
          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    );
  }

  return null;
}

/**
 * ThemeSegmentedControl - Segmented control for theme selection
 */
export function ThemeSegmentedControl({
  showSystem = true,
  className,
}) {
  const { theme, setTheme } = useTheme();

  const options = [
    { value: 'light', icon: SunIcon, label: 'Light' },
    { value: 'dark', icon: MoonIcon, label: 'Dark' },
    ...(showSystem ? [{ value: 'system', icon: ComputerDesktopIcon, label: 'System' }] : []),
  ];

  return (
    <div
      className={clsx(
        'inline-flex p-1 rounded-lg',
        'bg-gray-100 dark:bg-gray-800',
        className
      )}
      role="radiogroup"
      aria-label="Theme selection"
    >
      {options.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={clsx(
            'flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors',
            theme === value
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          )}
          role="radio"
          aria-checked={theme === value}
        >
          <Icon className="w-4 h-4" />
          <span className="text-sm font-medium">{label}</span>
        </button>
      ))}
    </div>
  );
}

export default ThemeToggle;
