import React, { useState } from 'react';
import { CodeBlock, InlineCode } from '../src/components/CodeBlock';
import { MermaidDiagram } from '../src/components/MermaidDiagram';
import { ThemeToggle, ThemeSegmentedControl } from '../src/components/ThemeToggle';

/**
 * CodeExample - Demonstrates CodeBlock and MermaidDiagram components
 */
export function CodeExample() {
  const [selectedLang, setSelectedLang] = useState('javascript');

  // Sample code snippets
  const codeExamples = {
    javascript: `// JavaScript Example
async function fetchUserData(userId) {
  try {
    const response = await fetch(\`/api/users/\${userId}\`);

    if (!response.ok) {
      throw new Error('User not found');
    }

    const userData = await response.json();
    return userData;
  } catch (error) {
    console.error('Failed to fetch user:', error);
    throw error;
  }
}

// Usage
const user = await fetchUserData(123);
console.log(user.name);`,

    python: `# Python Example
import asyncio
import aiohttp

async def fetch_user_data(user_id: int) -> dict:
    """Fetch user data from API."""
    async with aiohttp.ClientSession() as session:
        url = f"/api/users/{user_id}"

        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError("User not found")

            return await response.json()

# Usage
async def main():
    user = await fetch_user_data(123)
    print(user["name"])

asyncio.run(main())`,

    typescript: `// TypeScript Example
interface User {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
}

async function fetchUserData(userId: number): Promise<User> {
  const response = await fetch(\`/api/users/\${userId}\`);

  if (!response.ok) {
    throw new Error('User not found');
  }

  return response.json() as Promise<User>;
}

// Generic data fetcher
async function fetchData<T>(endpoint: string): Promise<T> {
  const response = await fetch(endpoint);
  return response.json();
}`,

    sql: `-- SQL Example
SELECT
    u.id,
    u.name,
    u.email,
    COUNT(o.id) as order_count,
    SUM(o.total) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    AND u.status = 'active'
GROUP BY u.id, u.name, u.email
HAVING total_spent > 100
ORDER BY total_spent DESC
LIMIT 10;`,

    bash: `#!/bin/bash
# Bash Example - Deploy Script

set -e

echo "Starting deployment..."

# Build the application
npm run build

# Run tests
npm test

# Deploy to production
if [ "$ENVIRONMENT" == "production" ]; then
    echo "Deploying to production..."
    aws s3 sync ./dist s3://my-bucket --delete
    aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
else
    echo "Deploying to staging..."
    aws s3 sync ./dist s3://staging-bucket --delete
fi

echo "Deployment complete!"`,

    json: `{
  "name": "aria-frontend-v2",
  "version": "2.0.0",
  "description": "Rich component library for ARIA",
  "dependencies": {
    "react": "^18.2.0",
    "recharts": "^2.10.3",
    "@tanstack/react-table": "^8.11.2"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest"
  }
}`,
  };

  // Mermaid diagrams
  const flowchartDef = `graph TD
    A[User Request] --> B{Authenticated?}
    B -->|Yes| C[Process Request]
    B -->|No| D[Return 401]
    C --> E{Valid Data?}
    E -->|Yes| F[Save to Database]
    E -->|No| G[Return 400]
    F --> H[Return Success]`;

  const sequenceDef = `sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant D as Database

    U->>F: Click Submit
    F->>A: POST /api/data
    A->>D: INSERT query
    D-->>A: Success
    A-->>F: 200 OK
    F-->>U: Show Success`;

  const classDef = `classDiagram
    class User {
        +int id
        +string name
        +string email
        +login()
        +logout()
    }
    class Order {
        +int id
        +int userId
        +float total
        +submit()
    }
    User "1" --> "*" Order: places`;

  const languages = ['javascript', 'python', 'typescript', 'sql', 'bash', 'json'];

  return (
    <div className="p-6 space-y-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Code & Diagram Examples
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Demonstration of CodeBlock and MermaidDiagram components.
            </p>
          </div>
          <ThemeSegmentedControl />
        </div>

        {/* Language Selector */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Syntax Highlighting
          </h2>

          <div className="flex flex-wrap gap-2 mb-4">
            {languages.map((lang) => (
              <button
                key={lang}
                onClick={() => setSelectedLang(lang)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
                  ${selectedLang === lang
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
              >
                {lang.charAt(0).toUpperCase() + lang.slice(1)}
              </button>
            ))}
          </div>

          <CodeBlock
            code={codeExamples[selectedLang]}
            language={selectedLang}
            title={`example.${selectedLang === 'javascript' ? 'js' : selectedLang === 'typescript' ? 'ts' : selectedLang === 'python' ? 'py' : selectedLang}`}
            showLineNumbers={true}
            showCopyButton={true}
          />
        </section>

        {/* Inline Code */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Inline Code
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Use the <InlineCode>InlineCode</InlineCode> component for inline code snippets like
            variable names (<InlineCode>userName</InlineCode>), function calls
            (<InlineCode>getData()</InlineCode>), or file paths
            (<InlineCode>/etc/nginx/nginx.conf</InlineCode>).
          </p>
        </section>

        {/* Line Highlighting */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Line Highlighting
          </h2>
          <CodeBlock
            code={`function processData(items) {
  // Filter valid items
  const valid = items.filter(item => item.active);

  // Transform data - IMPORTANT
  const transformed = valid.map(item => ({
    id: item.id,
    value: item.value * 2,
  }));

  return transformed;
}`}
            language="javascript"
            highlightLines={[5, 6, 7, 8]}
            showLineNumbers={true}
          />
        </section>

        {/* Mermaid Diagrams */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Mermaid Diagrams
          </h2>

          <div className="space-y-8">
            {/* Flowchart */}
            <div>
              <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">
                Flowchart
              </h3>
              <MermaidDiagram
                chart={flowchartDef}
                title="Request Processing Flow"
                zoomable={true}
              />
            </div>

            {/* Sequence Diagram */}
            <div>
              <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">
                Sequence Diagram
              </h3>
              <MermaidDiagram
                chart={sequenceDef}
                title="API Request Sequence"
                zoomable={true}
              />
            </div>

            {/* Class Diagram */}
            <div>
              <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-3">
                Class Diagram
              </h3>
              <MermaidDiagram
                chart={classDef}
                title="Data Model"
                zoomable={true}
              />
            </div>
          </div>
        </section>

        {/* Theme Toggle Examples */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Theme Toggle Variants
          </h2>

          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400 w-24">Icon:</span>
              <ThemeToggle variant="icon" />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400 w-24">Button:</span>
              <ThemeToggle variant="button" />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400 w-24">Switch:</span>
              <ThemeToggle variant="switch" />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400 w-24">Dropdown:</span>
              <ThemeToggle variant="dropdown" />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-gray-400 w-24">Segmented:</span>
              <ThemeSegmentedControl />
            </div>
          </div>
        </section>

        {/* Usage code */}
        <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
          <pre className="text-green-400 text-sm">
{`import { CodeBlock, InlineCode, MermaidDiagram, ThemeToggle } from 'aria-frontend-v2';

// Code block with syntax highlighting
<CodeBlock
  code={codeString}
  language="javascript"
  title="example.js"
  showLineNumbers={true}
  highlightLines={[3, 4, 5]}
/>

// Inline code
<p>Use the <InlineCode>useState</InlineCode> hook.</p>

// Mermaid diagram
<MermaidDiagram
  chart={\`graph TD
    A --> B
    B --> C
  \`}
  title="My Diagram"
  zoomable={true}
/>

// Theme toggle
<ThemeToggle variant="icon" />
<ThemeSegmentedControl />`}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default CodeExample;
