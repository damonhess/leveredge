import React, { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
} from '@tanstack/react-table';
import clsx from 'clsx';
import { ChevronUpIcon, ChevronDownIcon, ChevronUpDownIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

/**
 * DataTable Component - Sortable, filterable table with pagination
 *
 * @param {Object} props
 * @param {Array} props.data - Array of data objects
 * @param {Array} props.columns - Column definitions
 * @param {boolean} props.sortable - Enable column sorting
 * @param {boolean} props.filterable - Enable global filtering
 * @param {boolean} props.paginated - Enable pagination
 * @param {number} props.pageSize - Rows per page (default: 10)
 * @param {string} props.title - Table title
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.striped - Striped rows
 * @param {boolean} props.hoverable - Highlight row on hover
 * @param {boolean} props.compact - Compact row height
 */
export function DataTable({
  data = [],
  columns: columnDefs = [],
  sortable = true,
  filterable = true,
  paginated = true,
  pageSize = 10,
  title,
  className,
  striped = true,
  hoverable = true,
  compact = false,
  onRowClick,
  emptyMessage = 'No data available',
}) {
  const [sorting, setSorting] = useState([]);
  const [globalFilter, setGlobalFilter] = useState('');

  // Convert simple column definitions to TanStack format
  const columns = useMemo(() => {
    return columnDefs.map((col) => {
      if (typeof col === 'string') {
        return {
          accessorKey: col,
          header: col.charAt(0).toUpperCase() + col.slice(1).replace(/([A-Z])/g, ' $1'),
        };
      }
      return {
        accessorKey: col.key || col.accessorKey,
        header: col.header || col.label || col.key,
        cell: col.cell || col.render,
        enableSorting: col.sortable !== false,
        ...col,
      };
    });
  }, [columnDefs]);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: sortable ? getSortedRowModel() : undefined,
    getFilteredRowModel: filterable ? getFilteredRowModel() : undefined,
    getPaginationRowModel: paginated ? getPaginationRowModel() : undefined,
    initialState: {
      pagination: {
        pageSize,
      },
    },
  });

  const SortIcon = ({ column }) => {
    if (!column.getCanSort()) return null;
    const sorted = column.getIsSorted();
    if (sorted === 'asc') return <ChevronUpIcon className="w-4 h-4 ml-1" />;
    if (sorted === 'desc') return <ChevronDownIcon className="w-4 h-4 ml-1" />;
    return <ChevronUpDownIcon className="w-4 h-4 ml-1 opacity-50" />;
  };

  return (
    <div className={clsx('aria-data-table', className)}>
      {/* Header with title and search */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
        {title && (
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h3>
        )}
        {filterable && (
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder="Search..."
              className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                         bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         placeholder-gray-400 dark:placeholder-gray-500"
            />
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={clsx(
                      'px-4 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider',
                      compact ? 'py-2' : 'py-3',
                      header.column.getCanSort() && 'cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-700'
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortable && <SortIcon column={header.column} />}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-gray-500 dark:text-gray-400"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row, index) => (
                <tr
                  key={row.id}
                  onClick={() => onRowClick?.(row.original)}
                  className={clsx(
                    striped && index % 2 === 1 && 'bg-gray-50 dark:bg-gray-800/50',
                    hoverable && 'hover:bg-gray-100 dark:hover:bg-gray-800',
                    onRowClick && 'cursor-pointer'
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={clsx(
                        'px-4 text-sm text-gray-900 dark:text-gray-100',
                        compact ? 'py-2' : 'py-4'
                      )}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {paginated && table.getPageCount() > 1 && (
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mt-4">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Showing {table.getState().pagination.pageIndex * pageSize + 1} to{' '}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * pageSize,
              table.getFilteredRowModel().rows.length
            )}{' '}
            of {table.getFilteredRowModel().rows.length} results
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => table.setPageIndex(0)}
              disabled={!table.getCanPreviousPage()}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-800
                         text-gray-700 dark:text-gray-300"
            >
              First
            </button>
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-800
                         text-gray-700 dark:text-gray-300"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-gray-700 dark:text-gray-300">
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </span>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-800
                         text-gray-700 dark:text-gray-300"
            >
              Next
            </button>
            <button
              onClick={() => table.setPageIndex(table.getPageCount() - 1)}
              disabled={!table.getCanNextPage()}
              className="px-3 py-1 rounded border border-gray-300 dark:border-gray-600
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-800
                         text-gray-700 dark:text-gray-300"
            >
              Last
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataTable;
