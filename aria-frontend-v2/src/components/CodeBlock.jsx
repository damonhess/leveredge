import React, { useState, useCallback } from 'react';
import { Highlight, themes } from 'prism-react-renderer';
import clsx from 'clsx';
import { ClipboardIcon, ClipboardDocumentCheckIcon } from '@heroicons/react/24/outline';

// Language aliases mapping
const LANGUAGE_ALIASES = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  rb: 'ruby',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  md: 'markdown',
  dockerfile: 'docker',
};

// Language display names
const LANGUAGE_NAMES = {
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  python: 'Python',
  ruby: 'Ruby',
  bash: 'Bash',
  json: 'JSON',
  yaml: 'YAML',
  html: 'HTML',
  css: 'CSS',
  sql: 'SQL',
  go: 'Go',
  rust: 'Rust',
  java: 'Java',
  cpp: 'C++',
  c: 'C',
  csharp: 'C#',
  php: 'PHP',
  swift: 'Swift',
  kotlin: 'Kotlin',
  markdown: 'Markdown',
  docker: 'Dockerfile',
  graphql: 'GraphQL',
  jsx: 'JSX',
  tsx: 'TSX',
};

/**
 * CodeBlock Component - Syntax highlighted code with copy functionality
 *
 * @param {Object} props
 * @param {string} props.code - The code to display
 * @param {string} props.language - Programming language for highlighting
 * @param {string} props.title - Optional title/filename
 * @param {boolean} props.showLineNumbers - Show line numbers
 * @param {boolean} props.showCopyButton - Show copy to clipboard button
 * @param {number[]} props.highlightLines - Lines to highlight (1-indexed)
 * @param {number} props.startLine - Starting line number
 * @param {boolean} props.wrapLines - Wrap long lines
 * @param {string} props.className - Additional CSS classes
 * @param {string} props.theme - 'dark' | 'light' | 'auto'
 */
export function CodeBlock({
  code = '',
  language = 'text',
  title,
  showLineNumbers = true,
  showCopyButton = true,
  highlightLines = [],
  startLine = 1,
  wrapLines = false,
  className,
  theme: themeMode = 'auto',
  maxHeight,
}) {
  const [copied, setCopied] = useState(false);

  // Normalize language
  const normalizedLang = LANGUAGE_ALIASES[language?.toLowerCase()] || language?.toLowerCase() || 'text';
  const displayName = LANGUAGE_NAMES[normalizedLang] || normalizedLang.toUpperCase();

  // Determine theme based on mode
  const getTheme = useCallback(() => {
    if (themeMode === 'light') return themes.github;
    if (themeMode === 'dark') return themes.nightOwl;
    // Auto - check for dark mode class on document
    if (typeof document !== 'undefined' && document.documentElement.classList.contains('dark')) {
      return themes.nightOwl;
    }
    return themes.github;
  }, [themeMode]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  }, [code]);

  const isHighlighted = (lineNumber) => highlightLines.includes(lineNumber);

  return (
    <div className={clsx('aria-code-block rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      {(title || showCopyButton) && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            {title && (
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {title}
              </span>
            )}
            {!title && (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                {displayName}
              </span>
            )}
          </div>
          {showCopyButton && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded
                         text-gray-600 dark:text-gray-400
                         hover:bg-gray-200 dark:hover:bg-gray-700
                         transition-colors duration-150"
              title={copied ? 'Copied!' : 'Copy code'}
            >
              {copied ? (
                <>
                  <ClipboardDocumentCheckIcon className="w-4 h-4 text-green-500" />
                  <span className="text-green-500">Copied!</span>
                </>
              ) : (
                <>
                  <ClipboardIcon className="w-4 h-4" />
                  <span>Copy</span>
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Code content */}
      <Highlight
        theme={getTheme()}
        code={code.trim()}
        language={normalizedLang}
      >
        {({ className: hlClassName, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={clsx(
              hlClassName,
              'overflow-x-auto p-4 text-sm',
              wrapLines && 'whitespace-pre-wrap break-words'
            )}
            style={{
              ...style,
              margin: 0,
              maxHeight: maxHeight ? `${maxHeight}px` : undefined,
            }}
          >
            <code className="font-mono">
              {tokens.map((line, i) => {
                const lineNumber = startLine + i;
                const lineProps = getLineProps({ line, key: i });
                const highlighted = isHighlighted(lineNumber);

                return (
                  <div
                    key={i}
                    {...lineProps}
                    className={clsx(
                      lineProps.className,
                      'table-row',
                      highlighted && 'bg-yellow-100/50 dark:bg-yellow-900/30 -mx-4 px-4'
                    )}
                  >
                    {showLineNumbers && (
                      <span className="table-cell pr-4 text-right select-none text-gray-400 dark:text-gray-600 w-8">
                        {lineNumber}
                      </span>
                    )}
                    <span className="table-cell">
                      {line.map((token, key) => (
                        <span key={key} {...getTokenProps({ token, key })} />
                      ))}
                    </span>
                  </div>
                );
              })}
            </code>
          </pre>
        )}
      </Highlight>
    </div>
  );
}

/**
 * InlineCode Component - For inline code snippets
 */
export function InlineCode({ children, className }) {
  return (
    <code
      className={clsx(
        'px-1.5 py-0.5 rounded text-sm font-mono',
        'bg-gray-100 dark:bg-gray-800',
        'text-pink-600 dark:text-pink-400',
        'border border-gray-200 dark:border-gray-700',
        className
      )}
    >
      {children}
    </code>
  );
}

export default CodeBlock;
