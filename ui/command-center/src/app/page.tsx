'use client';

import { DOMAINS, AGENTS, COUNCIL_MEMBERS } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { DomainCard } from '@/components/dashboard/DomainCard';
import {
  Users, Activity, DollarSign, Calendar,
  MessageSquare, Zap, Server
} from 'lucide-react';
import Link from 'next/link';

export default function HubPage() {
  const daysToLaunch = Math.ceil(
    (new Date('2026-03-01').getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Command Center</h1>
        <p className="text-slate-400">LeverEdge AI Operations Hub</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Days to Launch"
          value={daysToLaunch}
          subtitle="March 1, 2026"
          icon={<Calendar size={20} />}
          color="#FBBF24"
        />
        <MetricCard
          title="Portfolio Value"
          value="$58K-$117K"
          subtitle="28 wins"
          icon={<DollarSign size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="Total Agents"
          value={Object.keys(AGENTS).length}
          subtitle="Across 8 domains"
          icon={<Users size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Council Members"
          value={COUNCIL_MEMBERS.length}
          subtitle="Available for meetings"
          icon={<MessageSquare size={20} />}
          color="#A78BFA"
        />
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Link
          href="/council/new"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
        >
          <MessageSquare size={18} />
          <span>New Council Meeting</span>
        </Link>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <Zap size={18} />
          <span>Quick Command</span>
        </button>
      </div>

      {/* Domains Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Domains</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.values(DOMAINS).map(domain => (
            <DomainCard key={domain.id} domain={domain} />
          ))}
        </div>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Server size={18} />
            System Health
          </h3>
          <div className="space-y-2">
            <HealthRow label="Database (Supabase)" status="healthy" />
            <HealthRow label="Event Bus" status="healthy" />
            <HealthRow label="n8n Control" status="healthy" />
            <HealthRow label="n8n Prod" status="healthy" />
            <HealthRow label="CONVENER" status="healthy" />
            <HealthRow label="Backups (CHRONOS)" status="healthy" />
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity size={18} />
            Recent Activity
          </h3>
          <div className="space-y-2 text-sm">
            <ActivityRow
              time="Just now"
              event="Command Center deployed"
            />
            <ActivityRow
              time="2m ago"
              event="CONVENER V2 upgraded"
            />
            <ActivityRow
              time="15m ago"
              event="CHRONOS backup successful"
            />
            <ActivityRow
              time="1h ago"
              event="SCHOLAR research completed"
            />
          </div>
        </div>
      </div>

      {/* Council Members Preview */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Council Members</h3>
          <Link href="/council" className="text-sm text-indigo-400 hover:text-indigo-300">
            View all
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          {COUNCIL_MEMBERS.map(agent => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}`}
              className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded-full text-sm transition"
            >
              {agent.name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function HealthRow({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className={`text-sm ${status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
        {status}
      </span>
    </div>
  );
}

function ActivityRow({ time, event }: { time: string; event: string }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className="text-xs text-slate-500 w-16 flex-shrink-0">{time}</span>
      <span className="text-slate-300">{event}</span>
    </div>
  );
}
