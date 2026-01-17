# ARIA Frontend V2

Rich React component library for ARIA AI Assistant responses. Provides interactive charts, data tables, syntax-highlighted code blocks, Mermaid diagrams, and more.

## Installation

```bash
npm install aria-frontend-v2
```

## Quick Start

```jsx
import { Chart, DataTable, CodeBlock, MermaidDiagram, ThemeProvider } from 'aria-frontend-v2';
import 'aria-frontend-v2/src/styles/globals.css';

function App() {
  return (
    <ThemeProvider>
      <Chart
        type="line"
        data={[
          { name: 'Jan', value: 100 },
          { name: 'Feb', value: 200 },
        ]}
        xKey="name"
        yKey="value"
      />
    </ThemeProvider>
  );
}
```

## Components

### Chart

Recharts wrapper supporting multiple chart types.

```jsx
import { Chart, LineChartComponent, BarChartComponent, PieChartComponent } from 'aria-frontend-v2';

// Generic chart component
<Chart
  type="line" // 'line' | 'bar' | 'pie' | 'area' | 'scatter' | 'radar'
  data={data}
  xKey="name"
  yKey="value" // or array: ['revenue', 'expenses']
  title="Monthly Revenue"
  height={300}
  showGrid={true}
  showLegend={true}
  showTooltip={true}
  colors={['#3b82f6', '#10b981']}
/>

// Convenience components
<LineChartComponent data={data} xKey="name" yKey="value" />
<BarChartComponent data={data} xKey="name" yKey={['a', 'b']} />
<PieChartComponent data={data} xKey="name" yKey="value" />
```

### DataTable

Sortable, filterable table with pagination.

```jsx
import { DataTable } from 'aria-frontend-v2';

const columns = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'email', header: 'Email' },
  {
    key: 'status',
    header: 'Status',
    cell: ({ getValue }) => <Badge>{getValue()}</Badge>,
  },
];

<DataTable
  data={users}
  columns={columns}
  title="Users"
  sortable={true}
  filterable={true}
  paginated={true}
  pageSize={10}
  striped={true}
  hoverable={true}
  onRowClick={(row) => console.log(row)}
/>
```

### CodeBlock

Syntax-highlighted code with copy functionality.

```jsx
import { CodeBlock, InlineCode } from 'aria-frontend-v2';

<CodeBlock
  code={codeString}
  language="javascript"
  title="example.js"
  showLineNumbers={true}
  showCopyButton={true}
  highlightLines={[3, 4, 5]}
  maxHeight={400}
/>

// Inline code
<p>Use the <InlineCode>useState</InlineCode> hook.</p>
```

Supported languages: javascript, typescript, python, ruby, bash, json, yaml, html, css, sql, go, rust, java, and more.

### MermaidDiagram

Mermaid diagram renderer with zoom support.

```jsx
import { MermaidDiagram, FlowchartDiagram, SequenceDiagram } from 'aria-frontend-v2';

<MermaidDiagram
  chart={`graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]
  `}
  title="Process Flow"
  zoomable={true}
/>

// Convenience components
<FlowchartDiagram definition="A --> B --> C" />
<SequenceDiagram definition="Alice->>Bob: Hello" />
```

### ImageGallery

Image gallery with lightbox.

```jsx
import { ImageGallery, SingleImage } from 'aria-frontend-v2';

<ImageGallery
  images={[
    { src: '/img1.jpg', alt: 'Image 1', title: 'First' },
    { src: '/img2.jpg', alt: 'Image 2', title: 'Second' },
  ]}
  columns={3}
  gap="md"
  showCaptions={true}
/>

<SingleImage src="/image.jpg" title="Photo" caption="Description" zoomable />
```

### AudioPlayer

Audio player with waveform visualization.

```jsx
import { AudioPlayer, AudioPlaylist } from 'aria-frontend-v2';

<AudioPlayer
  src="/audio.mp3"
  title="Track Name"
  artist="Artist"
  coverArt="/cover.jpg"
  showWaveform={true}
/>

<AudioPlaylist tracks={[...]} />
```

### PDFViewer

PDF viewer with page navigation.

```jsx
import { PDFViewer } from 'aria-frontend-v2';

<PDFViewer
  src="/document.pdf"
  title="Report"
  initialPage={1}
  initialScale={1}
  showControls={true}
  showDownload={true}
/>
```

### ThemeToggle

Dark/light mode toggle with multiple variants.

```jsx
import { ThemeToggle, ThemeSegmentedControl, ThemeProvider } from 'aria-frontend-v2';

// Wrap app with provider
<ThemeProvider defaultTheme="system">
  <App />
</ThemeProvider>

// Toggle variants
<ThemeToggle variant="icon" />
<ThemeToggle variant="button" />
<ThemeToggle variant="switch" />
<ThemeToggle variant="dropdown" showSystem />
<ThemeSegmentedControl />
```

## Hooks

### useTheme

Theme management hook.

```jsx
import { useTheme } from 'aria-frontend-v2';

function Component() {
  const { theme, setTheme, resolvedTheme, toggleTheme, isDark } = useTheme();

  return (
    <button onClick={toggleTheme}>
      Current: {resolvedTheme}
    </button>
  );
}
```

### useMediaQuery / useBreakpoints

Responsive breakpoint detection.

```jsx
import { useMediaQuery, useBreakpoints, useIsMobile, useIsDesktop } from 'aria-frontend-v2';

function Component() {
  const isLarge = useMediaQuery('(min-width: 1024px)');
  const { current, isMobile, isDesktop, breakpoint } = useBreakpoints();

  const columns = breakpoint({ xs: 1, sm: 2, lg: 3, xl: 4 });

  return <div>Current breakpoint: {current}</div>;
}
```

## Styling

### Tailwind CSS Setup

Add to your `tailwind.config.js`:

```js
module.exports = {
  content: [
    './src/**/*.{js,jsx}',
    './node_modules/aria-frontend-v2/src/**/*.{js,jsx}',
  ],
  darkMode: 'class',
  // ... rest of config
};
```

### CSS Variables

The library uses CSS custom properties for theming. Import the base styles:

```jsx
import 'aria-frontend-v2/src/styles/globals.css';
```

Or import just the theme variables:

```css
@import 'aria-frontend-v2/src/styles/themes.css';
```

### Preventing Flash of Wrong Theme

Add this script to your HTML `<head>`:

```jsx
import { themeScript } from 'aria-frontend-v2';

// In your HTML template
<script dangerouslySetInnerHTML={{ __html: themeScript }} />
```

## Integration with Existing ARIA Frontend

These components are designed as drop-in replacements:

```jsx
// Before (existing ARIA frontend)
<pre><code>{codeString}</code></pre>

// After (with V2 components)
<CodeBlock code={codeString} language="javascript" />
```

```jsx
// Before
<table>...</table>

// After
<DataTable data={data} columns={columns} />
```

## Browser Support

- Chrome 88+
- Firefox 85+
- Safari 14+
- Edge 88+

## Dependencies

- React 18+
- Recharts (charts)
- @tanstack/react-table (tables)
- prism-react-renderer (syntax highlighting)
- mermaid (diagrams)
- react-pdf (PDF viewer)
- wavesurfer.js (audio waveforms)
- yet-another-react-lightbox (image lightbox)
- Tailwind CSS (styling)

## License

MIT
