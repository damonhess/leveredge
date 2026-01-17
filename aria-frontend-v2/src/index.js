// ARIA Frontend V2 - Component Library Entry Point

// Components
export { Chart, LineChartComponent, BarChartComponent, PieChartComponent, AreaChartComponent, ScatterChartComponent, RadarChartComponent } from './components/Chart';
export { DataTable } from './components/DataTable';
export { CodeBlock, InlineCode } from './components/CodeBlock';
export { MermaidDiagram, FlowchartDiagram, SequenceDiagram, ClassDiagram, GanttChart, PieChart as MermaidPieChart, ERDiagram } from './components/MermaidDiagram';
export { ImageGallery, SingleImage } from './components/ImageGallery';
export { AudioPlayer, AudioPlaylist } from './components/AudioPlayer';
export { PDFViewer, PDFThumbnails } from './components/PDFViewer';
export { ThemeToggle, ThemeSegmentedControl } from './components/ThemeToggle';

// Hooks
export { useTheme, ThemeProvider, useThemeContext, themeScript } from './hooks/useTheme';
export {
  useMediaQuery,
  useBreakpoint,
  useBreakpoints,
  useIsMobile,
  useIsDesktop,
  usePrefersReducedMotion,
  usePrefersDarkMode,
  usePrefersHighContrast,
  useOrientation,
  useWindowSize,
  useContainerQuery,
} from './hooks/useMediaQuery';

// Styles (import these in your app)
// import 'aria-frontend-v2/src/styles/globals.css';
