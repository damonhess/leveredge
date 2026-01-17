interface StatusBadgeProps {
  status: string
}

const statusColors: Record<string, string> = {
  // Project statuses
  'active': 'bg-green-100 text-green-800',
  'in_progress': 'bg-blue-100 text-blue-800',
  'completed': 'bg-gray-100 text-gray-800',
  'on_hold': 'bg-yellow-100 text-yellow-800',
  'cancelled': 'bg-red-100 text-red-800',

  // Invoice statuses
  'paid': 'bg-green-100 text-green-800',
  'pending': 'bg-yellow-100 text-yellow-800',
  'overdue': 'bg-red-100 text-red-800',
  'draft': 'bg-gray-100 text-gray-800',

  // Support ticket statuses
  'open': 'bg-blue-100 text-blue-800',
  'in_review': 'bg-purple-100 text-purple-800',
  'resolved': 'bg-green-100 text-green-800',
  'closed': 'bg-gray-100 text-gray-800',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = statusColors[status.toLowerCase()] || 'bg-gray-100 text-gray-800'
  const displayStatus = status.replace(/_/g, ' ')

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${colorClass}`}>
      {displayStatus}
    </span>
  )
}
