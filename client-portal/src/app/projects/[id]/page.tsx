import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { ArrowLeft, Calendar, Clock } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import { notFound } from 'next/navigation'

interface ProjectDetailPageProps {
  params: {
    id: string
  }
}

export default async function ProjectDetailPage({ params }: ProjectDetailPageProps) {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  // Fetch client data based on auth user email
  const { data: client } = await supabase
    .from('clients')
    .select('*')
    .eq('email', user?.email ?? '')
    .single()

  // Fetch the project
  const { data: project } = await supabase
    .from('projects')
    .select('*')
    .eq('id', params.id)
    .eq('client_id', client?.id ?? '')
    .single()

  if (!project) {
    notFound()
  }

  return (
    <div>
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Projects
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <div className="mt-2 flex items-center gap-4">
              <StatusBadge status={project.status} />
              <span className="text-sm text-gray-500 flex items-center">
                <Calendar className="w-4 h-4 mr-1" />
                Created {new Date(project.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Project Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Overview</h2>
            <p className="text-gray-600">
              Project details and description will be displayed here.
              This is a placeholder for the full project information.
            </p>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Timeline</h2>
            <div className="text-gray-600">
              <p className="text-sm">Project timeline and milestones will be displayed here.</p>
              {/* Placeholder for timeline */}
              <div className="mt-4 space-y-4">
                <div className="flex items-start">
                  <div className="w-2 h-2 mt-2 rounded-full bg-green-500 mr-3"></div>
                  <div>
                    <p className="font-medium text-gray-900">Project Started</p>
                    <p className="text-sm text-gray-500">{new Date(project.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <div className="w-2 h-2 mt-2 rounded-full bg-primary-500 mr-3"></div>
                  <div>
                    <p className="font-medium text-gray-900">Current Phase</p>
                    <p className="text-sm text-gray-500">In progress</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Deliverables</h2>
            <p className="text-gray-500 text-sm">
              Project deliverables and files will be listed here.
            </p>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Info</h2>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={project.status} />
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Project ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{project.id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(project.created_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Need Help?</h2>
            <p className="text-sm text-gray-600 mb-4">
              Have questions about this project?
            </p>
            <Link href="/support" className="btn-primary w-full text-center block">
              Contact Support
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
