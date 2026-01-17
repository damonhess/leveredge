import React, { useState, useMemo } from 'react';
import { DataTable } from '../src/components/DataTable';

/**
 * TableExample - Demonstrates DataTable component features
 */
export function TableExample() {
  const [selectedRow, setSelectedRow] = useState(null);

  // Sample data - Users
  const userData = useMemo(() => [
    { id: 1, name: 'Alice Johnson', email: 'alice@example.com', role: 'Admin', status: 'Active', lastLogin: '2024-01-15' },
    { id: 2, name: 'Bob Smith', email: 'bob@example.com', role: 'Editor', status: 'Active', lastLogin: '2024-01-14' },
    { id: 3, name: 'Carol Williams', email: 'carol@example.com', role: 'Viewer', status: 'Inactive', lastLogin: '2024-01-10' },
    { id: 4, name: 'David Brown', email: 'david@example.com', role: 'Editor', status: 'Active', lastLogin: '2024-01-15' },
    { id: 5, name: 'Eve Davis', email: 'eve@example.com', role: 'Admin', status: 'Active', lastLogin: '2024-01-13' },
    { id: 6, name: 'Frank Miller', email: 'frank@example.com', role: 'Viewer', status: 'Pending', lastLogin: '2024-01-08' },
    { id: 7, name: 'Grace Wilson', email: 'grace@example.com', role: 'Editor', status: 'Active', lastLogin: '2024-01-15' },
    { id: 8, name: 'Henry Moore', email: 'henry@example.com', role: 'Viewer', status: 'Inactive', lastLogin: '2024-01-05' },
    { id: 9, name: 'Ivy Taylor', email: 'ivy@example.com', role: 'Admin', status: 'Active', lastLogin: '2024-01-14' },
    { id: 10, name: 'Jack Anderson', email: 'jack@example.com', role: 'Editor', status: 'Active', lastLogin: '2024-01-12' },
    { id: 11, name: 'Karen Thomas', email: 'karen@example.com', role: 'Viewer', status: 'Pending', lastLogin: '2024-01-09' },
    { id: 12, name: 'Leo Jackson', email: 'leo@example.com', role: 'Editor', status: 'Active', lastLogin: '2024-01-15' },
  ], []);

  // Sample data - Products
  const productData = useMemo(() => [
    { sku: 'PRD-001', name: 'Wireless Mouse', category: 'Electronics', price: 29.99, stock: 150, rating: 4.5 },
    { sku: 'PRD-002', name: 'Mechanical Keyboard', category: 'Electronics', price: 89.99, stock: 75, rating: 4.8 },
    { sku: 'PRD-003', name: 'USB-C Hub', category: 'Accessories', price: 45.00, stock: 200, rating: 4.2 },
    { sku: 'PRD-004', name: 'Monitor Stand', category: 'Furniture', price: 79.99, stock: 45, rating: 4.6 },
    { sku: 'PRD-005', name: 'Webcam HD', category: 'Electronics', price: 69.99, stock: 100, rating: 4.3 },
    { sku: 'PRD-006', name: 'Desk Lamp', category: 'Furniture', price: 35.00, stock: 80, rating: 4.1 },
  ], []);

  // Column definitions with custom rendering
  const userColumns = useMemo(() => [
    { key: 'id', header: 'ID', sortable: true },
    { key: 'name', header: 'Name', sortable: true },
    { key: 'email', header: 'Email', sortable: true },
    { key: 'role', header: 'Role', sortable: true },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      cell: ({ getValue }) => {
        const status = getValue();
        const colors = {
          Active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
          Inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
          Pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
        };
        return (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status]}`}>
            {status}
          </span>
        );
      },
    },
    { key: 'lastLogin', header: 'Last Login', sortable: true },
  ], []);

  const productColumns = useMemo(() => [
    { key: 'sku', header: 'SKU' },
    { key: 'name', header: 'Product Name' },
    { key: 'category', header: 'Category' },
    {
      key: 'price',
      header: 'Price',
      cell: ({ getValue }) => `$${getValue().toFixed(2)}`,
    },
    {
      key: 'stock',
      header: 'Stock',
      cell: ({ getValue }) => {
        const stock = getValue();
        const color = stock > 100 ? 'text-green-600' : stock > 50 ? 'text-yellow-600' : 'text-red-600';
        return <span className={color}>{stock}</span>;
      },
    },
    {
      key: 'rating',
      header: 'Rating',
      cell: ({ getValue }) => {
        const rating = getValue();
        return (
          <div className="flex items-center gap-1">
            <span className="text-yellow-500">{'★'.repeat(Math.floor(rating))}</span>
            <span className="text-gray-300 dark:text-gray-600">{'★'.repeat(5 - Math.floor(rating))}</span>
            <span className="ml-1 text-sm text-gray-600 dark:text-gray-400">{rating}</span>
          </div>
        );
      },
    },
  ], []);

  return (
    <div className="p-6 space-y-8 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          DataTable Examples
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Demonstration of the DataTable component with sorting, filtering, and pagination.
        </p>

        {/* Basic Table */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            User Management Table
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Full-featured table with sorting, filtering, pagination, and custom cell rendering.
          </p>

          <DataTable
            data={userData}
            columns={userColumns}
            title="Users"
            sortable={true}
            filterable={true}
            paginated={true}
            pageSize={5}
            striped={true}
            hoverable={true}
            onRowClick={(row) => setSelectedRow(row)}
          />

          {selectedRow && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-800 dark:text-blue-300">
                Selected: <strong>{selectedRow.name}</strong> ({selectedRow.email})
              </p>
            </div>
          )}
        </section>

        {/* Product Table */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Product Inventory Table
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Table with custom cell formatters for price, stock status, and ratings.
          </p>

          <DataTable
            data={productData}
            columns={productColumns}
            title="Products"
            sortable={true}
            filterable={true}
            paginated={false}
            striped={true}
            hoverable={true}
          />
        </section>

        {/* Simple Table */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Simple Table (Auto Columns)
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Table with auto-generated columns from string array.
          </p>

          <DataTable
            data={[
              { name: 'Project Alpha', status: 'In Progress', deadline: '2024-02-01' },
              { name: 'Project Beta', status: 'Completed', deadline: '2024-01-15' },
              { name: 'Project Gamma', status: 'Planning', deadline: '2024-03-01' },
            ]}
            columns={['name', 'status', 'deadline']}
            sortable={true}
            filterable={false}
            paginated={false}
            compact={true}
          />
        </section>

        {/* Compact Table */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Compact Table
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Compact variant with reduced padding for dense data display.
          </p>

          <DataTable
            data={userData.slice(0, 5)}
            columns={[
              { key: 'name', header: 'Name' },
              { key: 'role', header: 'Role' },
              { key: 'status', header: 'Status' },
            ]}
            sortable={true}
            filterable={false}
            paginated={false}
            compact={true}
            striped={false}
          />
        </section>

        {/* Usage code */}
        <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
          <pre className="text-green-400 text-sm">
{`import { DataTable } from 'aria-frontend-v2';

// Basic usage with auto columns
<DataTable
  data={data}
  columns={['name', 'email', 'role']}
/>

// Advanced usage with custom columns
const columns = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'email', header: 'Email' },
  {
    key: 'status',
    header: 'Status',
    cell: ({ getValue }) => (
      <span className="badge">{getValue()}</span>
    ),
  },
];

<DataTable
  data={data}
  columns={columns}
  title="Users"
  sortable={true}
  filterable={true}
  paginated={true}
  pageSize={10}
  onRowClick={(row) => console.log(row)}
/>`}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default TableExample;
