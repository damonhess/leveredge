'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import { LifeBuoy, Send, Clock, CheckCircle } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'

interface Ticket {
  id: string
  subject: string
  message: string
  status: string
  created_at: string
}

export default function SupportPage() {
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [clientId, setClientId] = useState<string | null>(null)

  const supabase = createClient()

  useEffect(() => {
    async function loadData() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      // Get client ID
      const { data: client } = await supabase
        .from('clients')
        .select('id')
        .eq('email', user.email ?? '')
        .single()

      if (client) {
        setClientId(client.id)

        // Load existing tickets
        const { data: existingTickets } = await supabase
          .from('support_tickets')
          .select('*')
          .eq('client_id', client.id)
          .order('created_at', { ascending: false })
          .limit(10)

        if (existingTickets) {
          setTickets(existingTickets)
        }
      }
    }

    loadData()
  }, [supabase])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    if (!clientId) {
      setError('Unable to identify your account. Please try again later.')
      setLoading(false)
      return
    }

    const { data, error: insertError } = await supabase
      .from('support_tickets')
      .insert({
        client_id: clientId,
        subject,
        message,
        status: 'open',
      })
      .select()
      .single()

    if (insertError) {
      setError(insertError.message)
      setLoading(false)
      return
    }

    // Add new ticket to the list
    if (data) {
      setTickets([data, ...tickets])
    }

    setSuccess(true)
    setSubject('')
    setMessage('')
    setLoading(false)

    // Clear success message after 5 seconds
    setTimeout(() => setSuccess(false), 5000)
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Support</h1>
        <p className="mt-1 text-gray-600">
          Submit a support ticket and we&apos;ll get back to you
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Submit Ticket Form */}
        <div className="card">
          <div className="flex items-center mb-6">
            <div className="p-2 bg-primary-100 rounded-lg mr-3">
              <LifeBuoy className="w-5 h-5 text-primary-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Submit a Ticket</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="subject" className="label">
                Subject
              </label>
              <input
                id="subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="input"
                placeholder="Brief description of your issue"
                required
              />
            </div>

            <div>
              <label htmlFor="message" className="label">
                Message
              </label>
              <textarea
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="input min-h-[150px] resize-y"
                placeholder="Please describe your issue in detail..."
                required
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-50 text-red-800 text-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="p-3 rounded-lg bg-green-50 text-green-800 text-sm flex items-center">
                <CheckCircle className="w-4 h-4 mr-2" />
                Your ticket has been submitted successfully!
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                'Submitting...'
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit Ticket
                </>
              )}
            </button>
          </form>
        </div>

        {/* Recent Tickets */}
        <div className="card">
          <div className="flex items-center mb-6">
            <div className="p-2 bg-gray-100 rounded-lg mr-3">
              <Clock className="w-5 h-5 text-gray-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Recent Tickets</h2>
          </div>

          {tickets.length > 0 ? (
            <div className="space-y-4">
              {tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="p-4 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-gray-900">{ticket.subject}</h3>
                    <StatusBadge status={ticket.status} />
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                    {ticket.message}
                  </p>
                  <p className="text-xs text-gray-500">
                    Submitted {new Date(ticket.created_at).toLocaleDateString()} at{' '}
                    {new Date(ticket.created_at).toLocaleTimeString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <LifeBuoy className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No support tickets yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Your submitted tickets will appear here
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Contact Info */}
      <div className="mt-6 card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Other Ways to Reach Us</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <p className="font-medium text-gray-900">Email</p>
            <p>support@leveredge.io</p>
          </div>
          <div>
            <p className="font-medium text-gray-900">Response Time</p>
            <p>Usually within 24 hours</p>
          </div>
        </div>
      </div>
    </div>
  )
}
