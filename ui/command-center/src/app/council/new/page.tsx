'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { COUNCIL_MEMBERS, DOMAINS } from '@/lib/agents';
import {
  ArrowLeft, Users, MessageSquare, Play,
  Check, X, ChevronDown
} from 'lucide-react';

function NewMeetingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const preselectedDomain = searchParams.get('domain');
  const preselectedAgent = searchParams.get('summon');

  const [topic, setTopic] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>(() => {
    if (preselectedAgent) {
      const member = COUNCIL_MEMBERS.find(m => m.name === preselectedAgent);
      return member ? [member.name] : [];
    }
    if (preselectedDomain) {
      const domain = DOMAINS[preselectedDomain];
      if (domain) {
        return COUNCIL_MEMBERS
          .filter(m => m.domain === preselectedDomain)
          .map(m => m.name);
      }
    }
    return [];
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showMemberDropdown, setShowMemberDropdown] = useState(false);

  const toggleMember = (memberName: string) => {
    setSelectedMembers(prev =>
      prev.includes(memberName)
        ? prev.filter(n => n !== memberName)
        : [...prev, memberName]
    );
  };

  const selectAll = () => {
    setSelectedMembers(COUNCIL_MEMBERS.map(m => m.name));
  };

  const clearAll = () => {
    setSelectedMembers([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!topic.trim() || selectedMembers.length === 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      // TODO: Call CONVENER API to create meeting
      // For now, simulate and redirect
      await new Promise(resolve => setTimeout(resolve, 500));

      // Redirect to the new meeting page
      router.push('/council/meeting-new');
    } catch (error) {
      console.error('Failed to create meeting:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/council"
          className="p-2 hover:bg-slate-800 rounded-lg transition"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">New Council Meeting</h1>
          <p className="text-slate-400">Convene the AI Council</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Topic */}
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <label className="block font-semibold mb-2">
            Meeting Topic
          </label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="What should the council discuss?"
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg focus:outline-none focus:border-indigo-500 transition"
          />
          <p className="text-xs text-slate-500 mt-2">
            Be specific about the topic to get better council deliberation.
          </p>
        </div>

        {/* Member Selection */}
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <label className="font-semibold flex items-center gap-2">
              <Users size={18} />
              Council Members
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={selectAll}
                className="text-xs text-indigo-400 hover:text-indigo-300"
              >
                Select All
              </button>
              <span className="text-slate-600">|</span>
              <button
                type="button"
                onClick={clearAll}
                className="text-xs text-slate-400 hover:text-slate-300"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Selected Members Preview */}
          <div
            className="flex flex-wrap gap-2 min-h-[40px] p-2 bg-slate-700/50 rounded-lg mb-4 cursor-pointer"
            onClick={() => setShowMemberDropdown(!showMemberDropdown)}
          >
            {selectedMembers.length === 0 ? (
              <span className="text-slate-500 text-sm">Click to select members...</span>
            ) : (
              selectedMembers.map(name => (
                <span
                  key={name}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded-full text-sm"
                >
                  {name}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleMember(name);
                    }}
                    className="hover:text-indigo-200"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))
            )}
            <ChevronDown
              size={16}
              className={`ml-auto text-slate-500 transition ${showMemberDropdown ? 'rotate-180' : ''}`}
            />
          </div>

          {/* Member Grid */}
          {showMemberDropdown && (
            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
              {COUNCIL_MEMBERS.map(member => {
                const isSelected = selectedMembers.includes(member.name);
                return (
                  <button
                    key={member.id}
                    type="button"
                    onClick={() => toggleMember(member.name)}
                    className={`flex items-center gap-2 p-2 rounded-lg transition text-left ${
                      isSelected
                        ? 'bg-indigo-500/20 border border-indigo-500/50'
                        : 'bg-slate-700/50 border border-transparent hover:bg-slate-700'
                    }`}
                  >
                    <div className={`w-6 h-6 rounded flex items-center justify-center ${
                      isSelected ? 'bg-indigo-500' : 'bg-slate-600'
                    }`}>
                      {isSelected && <Check size={14} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{member.name}</p>
                      <p className="text-xs text-slate-500 truncate">{member.function}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <p className="text-xs text-slate-500 mt-2">
            {selectedMembers.length} of {COUNCIL_MEMBERS.length} members selected
          </p>
        </div>

        {/* Meeting Options */}
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <label className="font-semibold mb-4 block">Meeting Options</label>
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                defaultChecked
                className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm">Enable voting on decisions</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                defaultChecked
                className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm">Record meeting transcript</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-indigo-500 focus:ring-indigo-500"
              />
              <span className="text-sm">Require unanimous decisions</span>
            </label>
          </div>
        </div>

        {/* Submit */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={isSubmitting || !topic.trim() || selectedMembers.length === 0}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition font-semibold"
          >
            <Play size={18} />
            {isSubmitting ? 'Convening...' : 'Convene Council'}
          </button>
          <Link
            href="/council"
            className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

export default function NewMeetingPage() {
  return (
    <Suspense fallback={<div className="text-slate-400">Loading...</div>}>
      <NewMeetingContent />
    </Suspense>
  );
}
