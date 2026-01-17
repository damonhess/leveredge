import { createClient } from '@/lib/supabase/server'
import { FileText, Download, DollarSign } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'

export default async function InvoicesPage() {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  // Fetch client data based on auth user email
  const { data: client } = await supabase
    .from('clients')
    .select('*')
    .eq('email', user?.email ?? '')
    .single()

  // Fetch all invoices
  const { data: invoices } = await supabase
    .from('invoices')
    .select('*')
    .eq('client_id', client?.id ?? '')
    .order('due_date', { ascending: false })

  // Calculate totals
  const totalPending = invoices
    ?.filter(i => i.status === 'pending')
    .reduce((sum, i) => sum + i.amount, 0) ?? 0

  const totalPaid = invoices
    ?.filter(i => i.status === 'paid')
    .reduce((sum, i) => sum + i.amount, 0) ?? 0

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
        <p className="mt-1 text-gray-600">
          View your invoice history and payment status
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <DollarSign className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending Payment</p>
              <p className="text-2xl font-semibold text-gray-900">
                ${totalPending.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-lg">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Paid</p>
              <p className="text-2xl font-semibold text-gray-900">
                ${totalPaid.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="card overflow-hidden">
        <div className="px-2 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Invoice History</h2>
        </div>

        {invoices && invoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Invoice ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Due Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-mono text-gray-900">
                        {invoice.id.substring(0, 8)}...
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-semibold text-gray-900">
                        ${invoice.amount.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {new Date(invoice.due_date).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={invoice.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        className="text-primary-600 hover:text-primary-800 text-sm font-medium inline-flex items-center"
                        title="Download invoice (placeholder)"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No invoices yet</h3>
            <p className="text-gray-500">
              Your invoices will appear here once they are generated.
            </p>
          </div>
        )}
      </div>

      {/* Payment Info Placeholder */}
      <div className="mt-6 card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Payment Information</h2>
        <p className="text-sm text-gray-600">
          For payment inquiries or to update your billing information, please contact our support team.
        </p>
      </div>
    </div>
  )
}
