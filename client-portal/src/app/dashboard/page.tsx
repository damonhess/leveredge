import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { FolderKanban, FileText, LifeBuoy, ArrowRight } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'

export default async function DashboardPage() {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  // Fetch client data based on auth user email
  const { data: client } = await supabase
    .from('clients')
    .select('*')
    .eq('email', user?.email ?? '')
    .single()

  // Fetch recent projects
  const { data: projects } = await supabase
    .from('projects')
    .select('*')
    .eq('client_id', client?.id ?? '')
    .order('created_at', { ascending: false })
    .limit(3)

  // Fetch recent invoices
  const { data: invoices } = await supabase
    .from('invoices')
    .select('*')
    .eq('client_id', client?.id ?? '')
    .order('due_date', { ascending: false })
    .limit(3)

  // Fetch recent tickets
  const { data: tickets } = await supabase
    .from('support_tickets')
    .select('*')
    .eq('client_id', client?.id ?? '')
    .order('created_at', { ascending: false })
    .limit(3)

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{client?.name ? `, ${client.name}` : ''}
        </h1>
        <p className="mt-1 text-gray-600">
          Here&apos;s an overview of your account
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-primary-100 rounded-lg">
              <FolderKanban className="w-6 h-6 text-primary-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Active Projects</p>
              <p className="text-2xl font-semibold text-gray-900">
                {projects?.filter(p => p.status === 'active' || p.status === 'in_progress').length ?? 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <FileText className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending Invoices</p>
              <p className="text-2xl font-semibold text-gray-900">
                {invoices?.filter(i => i.status === 'pending').length ?? 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-lg">
              <LifeBuoy className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Open Tickets</p>
              <p className="text-2xl font-semibold text-gray-900">
                {tickets?.filter(t => t.status === 'open' || t.status === 'in_review').length ?? 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Projects */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Projects</h2>
            <Link href="/projects" className="text-sm text-primary-600 hover:text-primary-500 flex items-center">
              View all <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
          <div className="space-y-3">
            {projects && projects.length > 0 ? (
              projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="block p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">{project.name}</span>
                    <StatusBadge status={project.status} />
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-gray-500 text-sm">No projects yet</p>
            )}
          </div>
        </div>

        {/* Recent Invoices */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Invoices</h2>
            <Link href="/invoices" className="text-sm text-primary-600 hover:text-primary-500 flex items-center">
              View all <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>
          <div className="space-y-3">
            {invoices && invoices.length > 0 ? (
              invoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-medium text-gray-900">
                        ${invoice.amount.toLocaleString()}
                      </span>
                      <p className="text-sm text-gray-500">
                        Due: {new Date(invoice.due_date).toLocaleDateString()}
                      </p>
                    </div>
                    <StatusBadge status={invoice.status} />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-500 text-sm">No invoices yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link href="/support" className="btn-primary inline-flex items-center">
            <LifeBuoy className="w-4 h-4 mr-2" />
            Submit Support Ticket
          </Link>
          <Link href="/projects" className="btn-secondary inline-flex items-center">
            <FolderKanban className="w-4 h-4 mr-2" />
            View All Projects
          </Link>
        </div>
      </div>
    </div>
  )
}
