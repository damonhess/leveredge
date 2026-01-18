'use client';

import Link from 'next/link';
import { COUNCIL_MEMBERS } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import {
  Users, MessageSquare, Calendar, Clock,
  Plus, History, Play
} from 'lucide-react';

// Static mock data for now - will be replaced with real API calls
const mockMeetings = [
  {
    id: 'meeting-001',
    topic: 'Q1 2026 Launch Strategy',
    status: 'completed',
    attendees: ['ATLAS', 'TYRION', 'ATHENA', 'DAVOS'],
    createdAt: '2026-01-15T10:00:00Z'
  },
  {
    id: 'meeting-002',
    topic: 'Infrastructure Scaling Review',
    status: 'completed',
    attendees: ['HEPHAESTUS', 'GENDRY', 'ATLAS'],
    createdAt: '2026-01-16T14:00:00Z'
  },
  {
    id: 'meeting-003',
    topic: 'Marketing Campaign Planning',
    status: 'active',
    attendees: ['CATALYST', 'SAGA', 'PRISM', 'SCHOLAR'],
    createdAt: '2026-01-18T09:00:00Z'
  }
];

export default function CouncilHubPage() {
  const activeMeetings = mockMeetings.filter(m => m.status === 'active');
  const completedMeetings = mockMeetings.filter(m => m.status === 'completed');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">The Council</h1>
        <p className="text-slate-400">AI Agent Deliberation Chamber</p>
      </div>

      {/* Council Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Council Members"
          value={COUNCIL_MEMBERS.length}
          subtitle="Available for meetings"
          icon={<Users size={20} />}
          color="#A78BFA"
        />
        <MetricCard
          title="Active Meetings"
          value={activeMeetings.length}
          subtitle="In progress"
          icon={<Play size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="This Week"
          value={mockMeetings.length}
          subtitle="Total meetings"
          icon={<Calendar size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Avg Duration"
          value="12m"
          subtitle="Per meeting"
          icon={<Clock size={20} />}
          color="#FBBF24"
        />
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Link
          href="/council/new"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
        >
          <Plus size={18} />
          <span>New Meeting</span>
        </Link>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <History size={18} />
          <span>View History</span>
        </button>
      </div>

      {/* Active Meetings */}
      {activeMeetings.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Play size={18} className="text-green-400" />
            Active Meetings
          </h2>
          <div className="space-y-3">
            {activeMeetings.map(meeting => (
              <MeetingCard key={meeting.id} meeting={meeting} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Meetings */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <History size={18} className="text-slate-400" />
          Recent Meetings
        </h2>
        <div className="space-y-3">
          {completedMeetings.map(meeting => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </div>
      </div>

      {/* Council Members Grid */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Users size={18} />
          Council Members
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {COUNCIL_MEMBERS.map(member => (
            <Link
              key={member.id}
              href={`/agents/${member.id}`}
              className="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition"
            >
              <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold text-sm">
                {member.name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{member.name}</p>
                <p className="text-xs text-slate-500 truncate">{member.function}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

interface Meeting {
  id: string;
  topic: string;
  status: string;
  attendees: string[];
  createdAt: string;
}

function MeetingCard({ meeting }: { meeting: Meeting }) {
  const statusColors = {
    active: 'bg-green-500/20 text-green-400',
    completed: 'bg-slate-500/20 text-slate-400',
    scheduled: 'bg-blue-500/20 text-blue-400'
  };

  const statusColor = statusColors[meeting.status as keyof typeof statusColors] || statusColors.scheduled;

  return (
    <Link
      href={`/council/${meeting.id}`}
      className="block bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">{meeting.topic}</h3>
            <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor}`}>
              {meeting.status}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            {meeting.attendees.length} attendees: {meeting.attendees.join(', ')}
          </p>
        </div>
        <span className="text-xs text-slate-500">
          {new Date(meeting.createdAt).toLocaleDateString()}
        </span>
      </div>
    </Link>
  );
}
