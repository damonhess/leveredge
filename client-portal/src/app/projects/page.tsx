import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { FolderKanban, ChevronRight } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'

export default async function ProjectsPage() {
  const supabase = await createClient()

  const { data: { user } } = await supabase.auth.getUser()

  // Fetch client data based on auth user email
  const { data: client } = await supabase
    .from('clients')
    .select('*')
    .eq('email', user?.email ?? '')
    .single()

  // Fetch all projects
  const { data: projects } = await supabase
    .from('projects')
    .select('*')
    .eq('client_id', client?.id ?? '')
    .order('created_at', { ascending: false })

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <p className="mt-1 text-gray-600">
          View and track all your projects
        </p>
      </div>

      {/* Projects List */}
      <div className="card">
        {projects && projects.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center justify-between py-4 px-2 hover:bg-gray-50 rounded-lg transition-colors -mx-2"
              >
                <div className="flex items-center">
                  <div className="p-2 bg-primary-100 rounded-lg mr-4">
                    <FolderKanban className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{project.name}</h3>
                    <p className="text-sm text-gray-500">
                      Created {new Date(project.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <StatusBadge status={project.status} />
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <FolderKanban className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No projects yet</h3>
            <p className="text-gray-500">
              Your projects will appear here once they are created.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
