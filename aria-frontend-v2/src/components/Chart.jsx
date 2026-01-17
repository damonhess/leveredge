import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';
import clsx from 'clsx';

const COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#84cc16', // lime-500
];

const CHART_TYPES = {
  line: 'line',
  bar: 'bar',
  pie: 'pie',
  area: 'area',
  scatter: 'scatter',
  radar: 'radar',
};

/**
 * Chart Component - Recharts wrapper for various chart types
 *
 * @param {Object} props
 * @param {string} props.type - Chart type: 'line' | 'bar' | 'pie' | 'area' | 'scatter' | 'radar'
 * @param {Array} props.data - Data array for the chart
 * @param {string} props.xKey - Key for X-axis data
 * @param {string|string[]} props.yKey - Key(s) for Y-axis data
 * @param {string} props.title - Chart title
 * @param {number} props.height - Chart height in pixels
 * @param {boolean} props.showGrid - Show grid lines
 * @param {boolean} props.showLegend - Show legend
 * @param {boolean} props.showTooltip - Show tooltip on hover
 * @param {string[]} props.colors - Custom color palette
 * @param {string} props.className - Additional CSS classes
 */
export function Chart({
  type = 'line',
  data = [],
  xKey = 'name',
  yKey = 'value',
  title,
  height = 300,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  colors = COLORS,
  className,
  ...props
}) {
  const yKeys = useMemo(() =>
    Array.isArray(yKey) ? yKey : [yKey],
    [yKey]
  );

  const commonProps = {
    data,
    margin: { top: 20, right: 30, left: 20, bottom: 20 },
  };

  const renderChart = () => {
    switch (type) {
      case CHART_TYPES.line:
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />}
            <XAxis
              dataKey={xKey}
              className="text-gray-600 dark:text-gray-400"
              tick={{ fill: 'currentColor' }}
            />
            <YAxis
              className="text-gray-600 dark:text-gray-400"
              tick={{ fill: 'currentColor' }}
            />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        );

      case CHART_TYPES.bar:
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />}
            <XAxis
              dataKey={xKey}
              tick={{ fill: 'currentColor' }}
            />
            <YAxis tick={{ fill: 'currentColor' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        );

      case CHART_TYPES.pie:
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={yKeys[0]}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={height / 3}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
          </PieChart>
        );

      case CHART_TYPES.area:
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />}
            <XAxis dataKey={xKey} tick={{ fill: 'currentColor' }} />
            <YAxis tick={{ fill: 'currentColor' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
            {yKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
          </AreaChart>
        );

      case CHART_TYPES.scatter:
        return (
          <ScatterChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />}
            <XAxis dataKey={xKey} tick={{ fill: 'currentColor' }} />
            <YAxis dataKey={yKeys[0]} tick={{ fill: 'currentColor' }} />
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
            <Scatter name={yKeys[0]} data={data} fill={colors[0]} />
          </ScatterChart>
        );

      case CHART_TYPES.radar:
        return (
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid className="stroke-gray-200 dark:stroke-gray-700" />
            <PolarAngleAxis dataKey={xKey} tick={{ fill: 'currentColor' }} />
            <PolarRadiusAxis tick={{ fill: 'currentColor' }} />
            {yKeys.map((key, index) => (
              <Radar
                key={key}
                name={key}
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
            {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'var(--tooltip-bg)', borderColor: 'var(--tooltip-border)' }} />}
            {showLegend && <Legend />}
          </RadarChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className={clsx('aria-chart', className)} {...props}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 text-center">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}

// Convenience components for specific chart types
export const LineChartComponent = (props) => <Chart type="line" {...props} />;
export const BarChartComponent = (props) => <Chart type="bar" {...props} />;
export const PieChartComponent = (props) => <Chart type="pie" {...props} />;
export const AreaChartComponent = (props) => <Chart type="area" {...props} />;
export const ScatterChartComponent = (props) => <Chart type="scatter" {...props} />;
export const RadarChartComponent = (props) => <Chart type="radar" {...props} />;

export default Chart;
