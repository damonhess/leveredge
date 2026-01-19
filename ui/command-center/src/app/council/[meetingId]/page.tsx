'use client';

import { useState } from 'react';
import Link from 'next/link';
import { COUNCIL_MEMBERS, AGENTS } from '@/lib/agents';
import {
  ArrowLeft, MessageSquare, Users, ThumbsUp, ThumbsDown,
  Hand, UserPlus, Gavel, FileText, Send, Clock, CheckCircle
} from 'lucide-react';

interface MeetingPageProps {
  params: { meetingId: string };
}

// Mock meeting data - will be replaced with real API
const mockMeeting = {
  id: 'meeting-001',
  topic: 'Q1 2026 Launch Strategy Discussion',
  status: 'active',
  attendees: ['ATLAS', 'TYRION', 'ATHENA', 'DAVOS', 'CATALYST'],
  guests: [
    { guest_id: 'guest_launch_coach_abc123', name: 'LAUNCH_COACH', display_name: 'Launch Coach (Claude Web)', connection_type: 'mcp' }
  ],
  invitedGuests: ['LAUNCH_COACH'],
  currentSpeaker: 'ATLAS',
  floorQueue: ['TYRION', 'ATHENA'],
  transcript: [
    { speaker: 'CONVENER', message: 'Meeting convened. Topic: Q1 2026 Launch Strategy Discussion', time: '09:00' },
    { speaker: 'ATLAS', message: 'Thank you. I propose we focus on three key areas: infrastructure readiness, marketing launch, and partner integrations. [YIELD]', time: '09:01' },
    { speaker: 'CONVENER', message: 'ATLAS yields the floor. TYRION, you have the floor.', time: '09:02' },
    { speaker: 'TYRION', message: 'I agree with the framework. However, I believe we should prioritize partner integrations first - they have the longest lead time. [QUESTION: DAVOS]', time: '09:03' },
    { speaker: 'DAVOS', message: 'From a business perspective, TYRION is correct. Partner agreements typically take 4-6 weeks to finalize. We should start those conversations immediately.', time: '09:04' },
    { speaker: 'LAUNCH_COACH', message: 'I concur with DAVOS. Based on today\'s build velocity, I recommend aggressive timelines. The team has proven it can execute faster than estimated.', time: '09:05', isGuest: true },
  ],
  decisions: [
    { text: 'Prioritize partner integrations in Q1 timeline', votes: { for: 4, against: 1 }, status: 'passed' }
  ]
};

export default function MeetingPage({ params }: MeetingPageProps) {
  const [message, setMessage] = useState('');
  const [showSummonModal, setShowSummonModal] = useState(false);
  const [showVoteModal, setShowVoteModal] = useState(false);
  const [currentVote, setCurrentVote] = useState<string | null>(null);

  const meeting = mockMeeting; // Will be replaced with real data fetch

  const handleSend = () => {
    if (!message.trim()) return;
    // TODO: Call CONVENER /speak endpoint
    console.log('Sending message:', message);
    setMessage('');
  };

  const handleRequestFloor = () => {
    // TODO: Call CONVENER to request floor
    console.log('Requesting floor');
  };

  const handleCallVote = () => {
    setShowVoteModal(true);
  };

  const handleSummon = (agentName: string) => {
    // TODO: Call CONVENER /summon endpoint
    console.log('Summoning:', agentName);
    setShowSummonModal(false);
  };

  const handleAdjourn = () => {
    // TODO: Call CONVENER /adjourn-v2 endpoint
    console.log('Adjourning meeting');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <Link
            href="/council"
            className="p-2 hover:bg-slate-800 rounded-lg transition"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold">{meeting.topic}</h1>
              <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full text-xs">
                {meeting.status}
              </span>
            </div>
            <p className="text-sm text-slate-400">
              {meeting.attendees.length} attendees
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSummonModal(true)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
          >
            <UserPlus size={16} />
            Summon
          </button>
          <button
            onClick={handleAdjourn}
            className="flex items-center gap-2 px-3 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition text-sm"
          >
            <Gavel size={16} />
            Adjourn
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 pt-4 overflow-hidden">
        {/* Transcript Panel */}
        <div className="flex-1 flex flex-col bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="p-3 border-b border-slate-700 flex items-center gap-2">
            <FileText size={16} />
            <span className="font-semibold">Transcript</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {meeting.transcript.map((entry, idx) => (
              <TranscriptEntry key={idx} entry={entry} />
            ))}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-slate-700">
            <div className="flex gap-2">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Enter your contribution..."
                className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-indigo-500 transition text-sm"
              />
              <button
                onClick={handleSend}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Side Panel */}
        <div className="w-72 space-y-4 overflow-y-auto">
          {/* Current Speaker */}
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
              <MessageSquare size={14} />
              Current Speaker
            </h3>
            <div className="flex items-center gap-3 p-2 bg-green-500/10 rounded-lg border border-green-500/30">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 font-bold text-sm">
                {meeting.currentSpeaker.charAt(0)}
              </div>
              <span className="font-semibold text-green-400">{meeting.currentSpeaker}</span>
            </div>
          </div>

          {/* Floor Queue */}
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
              <Hand size={14} />
              Floor Queue
            </h3>
            {meeting.floorQueue.length > 0 ? (
              <div className="space-y-2">
                {meeting.floorQueue.map((name, idx) => (
                  <div key={name} className="flex items-center gap-2 text-sm">
                    <span className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center text-xs">
                      {idx + 1}
                    </span>
                    <span>{name}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No one in queue</p>
            )}
            <button
              onClick={handleRequestFloor}
              className="w-full mt-3 flex items-center justify-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
            >
              <Hand size={14} />
              Request Floor
            </button>
          </div>

          {/* Attendees */}
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
              <Users size={14} />
              Attendees ({meeting.attendees.length})
            </h3>
            <div className="space-y-2">
              {meeting.attendees.map(name => {
                const agent = AGENTS[name];
                return (
                  <div key={name} className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span>{name}</span>
                    {name === meeting.currentSpeaker && (
                      <MessageSquare size={12} className="text-green-400" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Guests */}
          {(meeting.guests.length > 0 || meeting.invitedGuests.length > 0) && (
            <div className="bg-slate-800 rounded-xl p-4 border border-purple-500/30">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm text-purple-400">
                <UserPlus size={14} />
                Guest Advisors
              </h3>
              <div className="space-y-2">
                {meeting.guests.map(guest => (
                  <div key={guest.guest_id} className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 rounded-full bg-purple-400" />
                    <span>{guest.display_name}</span>
                    <span className="text-xs text-slate-500">({guest.connection_type})</span>
                  </div>
                ))}
                {meeting.invitedGuests
                  .filter(name => !meeting.guests.some(g => g.name === name))
                  .map(name => (
                    <div key={name} className="flex items-center gap-2 text-sm text-slate-500">
                      <div className="w-2 h-2 rounded-full bg-slate-600" />
                      <span>{name}</span>
                      <span className="text-xs">(waiting)</span>
                    </div>
                  ))
                }
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Advisory only - no voting authority
              </p>
            </div>
          )}

          {/* Decisions */}
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
              <Gavel size={14} />
              Decisions
            </h3>
            {meeting.decisions.length > 0 ? (
              <div className="space-y-2">
                {meeting.decisions.map((decision, idx) => (
                  <div key={idx} className="p-2 bg-slate-700/50 rounded-lg text-sm">
                    <p className="mb-2">{decision.text}</p>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-green-400 flex items-center gap-1">
                        <ThumbsUp size={12} /> {decision.votes.for}
                      </span>
                      <span className="text-red-400 flex items-center gap-1">
                        <ThumbsDown size={12} /> {decision.votes.against}
                      </span>
                      <span className={`ml-auto ${decision.status === 'passed' ? 'text-green-400' : 'text-red-400'}`}>
                        {decision.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No decisions yet</p>
            )}
            <button
              onClick={handleCallVote}
              className="w-full mt-3 flex items-center justify-center gap-2 px-3 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 rounded-lg transition text-sm"
            >
              <Gavel size={14} />
              Call Vote
            </button>
          </div>
        </div>
      </div>

      {/* Summon Modal */}
      {showSummonModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 w-96 max-h-[80vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">Summon Council Member</h2>
            <div className="space-y-2">
              {COUNCIL_MEMBERS.filter(m => !meeting.attendees.includes(m.name)).map(member => (
                <button
                  key={member.id}
                  onClick={() => handleSummon(member.name)}
                  className="w-full flex items-center gap-3 p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition text-left"
                >
                  <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold text-sm">
                    {member.name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium">{member.name}</p>
                    <p className="text-xs text-slate-500">{member.function}</p>
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowSummonModal(false)}
              className="w-full mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Vote Modal */}
      {showVoteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 w-96">
            <h2 className="text-lg font-bold mb-4">Call for Vote</h2>
            <textarea
              value={currentVote || ''}
              onChange={(e) => setCurrentVote(e.target.value)}
              placeholder="What motion should be voted on?"
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-indigo-500 transition h-24 resize-none"
            />
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  // TODO: Call CONVENER /vote endpoint
                  console.log('Calling vote:', currentVote);
                  setShowVoteModal(false);
                  setCurrentVote(null);
                }}
                className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
              >
                Call Vote
              </button>
              <button
                onClick={() => {
                  setShowVoteModal(false);
                  setCurrentVote(null);
                }}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface TranscriptEntryData {
  speaker: string;
  message: string;
  time: string;
  isGuest?: boolean;
}

function TranscriptEntry({ entry }: { entry: TranscriptEntryData }) {
  const isSystem = entry.speaker === 'CONVENER';
  const isGuest = entry.isGuest;

  if (isSystem) {
    return (
      <div className="flex items-start gap-3 text-sm">
        <Clock size={14} className="text-slate-500 mt-1 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-slate-500 italic">{entry.message}</p>
          <span className="text-xs text-slate-600">{entry.time}</span>
        </div>
      </div>
    );
  }

  const agent = AGENTS[entry.speaker];

  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
        isGuest
          ? 'bg-purple-500/20 text-purple-400 ring-1 ring-purple-500/50'
          : 'bg-indigo-500/20 text-indigo-400'
      }`}>
        {isGuest ? '👤' : entry.speaker.charAt(0)}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className={`font-semibold text-sm ${isGuest ? 'text-purple-400' : ''}`}>
            {entry.speaker}
          </span>
          {isGuest && (
            <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded">
              guest
            </span>
          )}
          <span className="text-xs text-slate-500">{entry.time}</span>
        </div>
        <p className="text-sm text-slate-300 mt-1">{entry.message}</p>
      </div>
    </div>
  );
}
