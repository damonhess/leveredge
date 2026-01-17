import React, { useState } from 'react';
import { Chart, LineChartComponent, BarChartComponent, PieChartComponent, AreaChartComponent } from '../src/components/Chart';

/**
 * ChartExample - Demonstrates various chart types and configurations
 */
export function ChartExample() {
  const [chartType, setChartType] = useState('line');

  // Sample data for different chart types
  const monthlyData = [
    { name: 'Jan', revenue: 4000, expenses: 2400, profit: 1600 },
    { name: 'Feb', revenue: 3000, expenses: 1398, profit: 1602 },
    { name: 'Mar', revenue: 2000, expenses: 9800, profit: -7800 },
    { name: 'Apr', revenue: 2780, expenses: 3908, profit: -1128 },
    { name: 'May', revenue: 1890, expenses: 4800, profit: -2910 },
    { name: 'Jun', revenue: 2390, expenses: 3800, profit: -1410 },
    { name: 'Jul', revenue: 3490, expenses: 4300, profit: -810 },
  ];

  const pieData = [
    { name: 'Marketing', value: 400 },
    { name: 'Sales', value: 300 },
    { name: 'Engineering', value: 300 },
    { name: 'Support', value: 200 },
    { name: 'Operations', value: 100 },
  ];

  const radarData = [
    { subject: 'Performance', A: 120, B: 110 },
    { subject: 'Reliability', A: 98, B: 130 },
    { subject: 'Security', A: 86, B: 130 },
    { subject: 'Usability', A: 99, B: 100 },
    { subject: 'Scalability', A: 85, B: 90 },
    { subject: 'Support', A: 65, B: 85 },
  ];

  return (
    <div className="p-6 space-y-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Chart Examples
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Demonstration of the Chart component with various configurations.
        </p>

        {/* Chart type selector */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Select Chart Type
          </label>
          <div className="flex flex-wrap gap-2">
            {['line', 'bar', 'area', 'pie', 'radar', 'scatter'].map((type) => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
                  ${chartType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic chart based on selection */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <Chart
            type={chartType}
            data={chartType === 'pie' ? pieData : chartType === 'radar' ? radarData : monthlyData}
            xKey={chartType === 'radar' ? 'subject' : 'name'}
            yKey={chartType === 'pie' ? 'value' : chartType === 'radar' ? ['A', 'B'] : ['revenue', 'expenses']}
            title={`${chartType.charAt(0).toUpperCase() + chartType.slice(1)} Chart Example`}
            height={350}
            showGrid={chartType !== 'pie'}
            showLegend={true}
            showTooltip={true}
          />
        </div>

        {/* Multiple charts side by side */}
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Multiple Charts
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Line Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <LineChartComponent
              data={monthlyData}
              xKey="name"
              yKey="revenue"
              title="Monthly Revenue"
              height={250}
            />
          </div>

          {/* Bar Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <BarChartComponent
              data={monthlyData}
              xKey="name"
              yKey={['revenue', 'expenses']}
              title="Revenue vs Expenses"
              height={250}
            />
          </div>

          {/* Pie Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <PieChartComponent
              data={pieData}
              xKey="name"
              yKey="value"
              title="Budget Distribution"
              height={250}
            />
          </div>

          {/* Area Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <AreaChartComponent
              data={monthlyData}
              xKey="name"
              yKey="profit"
              title="Monthly Profit"
              height={250}
              colors={['#10b981']}
            />
          </div>
        </div>

        {/* Customization Example */}
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Customized Chart
        </h2>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <Chart
            type="line"
            data={monthlyData}
            xKey="name"
            yKey={['revenue', 'expenses', 'profit']}
            title="Financial Overview"
            height={400}
            colors={['#3b82f6', '#ef4444', '#10b981']}
            showGrid={true}
            showLegend={true}
            showTooltip={true}
          />
        </div>

        {/* Usage code */}
        <div className="mt-8 bg-gray-900 rounded-lg p-4 overflow-x-auto">
          <pre className="text-green-400 text-sm">
{`import { Chart, LineChartComponent } from 'aria-frontend-v2';

// Basic usage
<Chart
  type="line"
  data={data}
  xKey="name"
  yKey="value"
  title="My Chart"
/>

// Multiple series
<Chart
  type="bar"
  data={data}
  xKey="name"
  yKey={['revenue', 'expenses']}
  colors={['#3b82f6', '#ef4444']}
/>

// Convenience components
<LineChartComponent data={data} xKey="name" yKey="value" />
<BarChartComponent data={data} xKey="name" yKey="value" />
<PieChartComponent data={data} xKey="name" yKey="value" />`}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default ChartExample;
