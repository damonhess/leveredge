'use client';

import { notFound } from 'next/navigation';
import Link from 'next/link';
import { DOMAINS, getAgentsByDomain, AGENTS } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { AgentStatus } from '@/components/dashboard/AgentStatus';
import {
  Users, ArrowLeft, Shield, Zap,
  MessageSquare, Settings, Activity
} from 'lucide-react';

interface DomainPageProps {
  params: { domain: string };
}

export default function DomainPage({ params }: DomainPageProps) {
  const domainId = params.domain;
  const domain = DOMAINS[domainId];

  if (!domain) {
    notFound();
  }

  const agents = getAgentsByDomain(domainId);
  const supervisor = AGENTS[domain.supervisor];
  const councilMembers = agents.filter(a => a.councilMember);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="p-2 hover:bg-slate-800 rounded-lg transition"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: domain.color }}>
            {domain.name}
          </h1>
          <p className="text-slate-400">{domain.theme}</p>
        </div>
      </div>

      {/* Domain Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Agents"
          value={agents.length}
          subtitle="In this domain"
          icon={<Users size={20} />}
          color={domain.color}
        />
        <MetricCard
          title="Council Members"
          value={councilMembers.length}
          subtitle="Can attend meetings"
          icon={<MessageSquare size={20} />}
          color="#A78BFA"
        />
        <MetricCard
          title="Supervisor"
          value={domain.supervisor}
          subtitle="Domain lead"
          icon={<Shield size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Status"
          value="Online"
          subtitle="All systems operational"
          icon={<Activity size={20} />}
          color="#34D399"
        />
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Link
          href={`/council/new?domain=${domainId}`}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
        >
          <MessageSquare size={18} />
          <span>Domain Council</span>
        </Link>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <Zap size={18} />
          <span>Quick Command</span>
        </button>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <Settings size={18} />
          <span>Domain Settings</span>
        </button>
      </div>

      {/* Agents Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Domain Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(agent => (
            <Link key={agent.id} href={`/agents/${agent.id}`}>
              <AgentCard agent={agent} domainColor={domain.color} />
            </Link>
          ))}
        </div>
      </div>

      {/* Supervisor Panel */}
      {supervisor && (
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Shield size={18} style={{ color: domain.color }} />
            Domain Supervisor
          </h3>
          <Link
            href={`/agents/${supervisor.id}`}
            className="flex items-center gap-4 p-4 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition"
          >
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold"
              style={{ backgroundColor: domain.color + '30', color: domain.color }}
            >
              {supervisor.name.charAt(0)}
            </div>
            <div>
              <p className="font-semibold">{supervisor.name}</p>
              <p className="text-sm text-slate-400">{supervisor.function}</p>
              {supervisor.port > 0 && (
                <p className="text-xs text-slate-500 mt-1">Port: {supervisor.port}</p>
              )}
            </div>
          </Link>
        </div>
      )}

      {/* Council Members */}
      {councilMembers.length > 0 && (
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <MessageSquare size={18} className="text-indigo-400" />
            Council Members from {domain.name}
          </h3>
          <div className="flex flex-wrap gap-2">
            {councilMembers.map(agent => (
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
      )}
    </div>
  );
}

function AgentCard({ agent, domainColor }: { agent: { id: string; name: string; function: string; port: number; councilMember?: boolean; supervisor?: boolean }; domainColor: string }) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition">
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
          style={{ backgroundColor: domainColor + '30', color: domainColor }}
        >
          {agent.name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-semibold truncate">{agent.name}</p>
            {agent.supervisor && (
              <Shield size={14} className="text-blue-400 flex-shrink-0" />
            )}
            {agent.councilMember && (
              <MessageSquare size={14} className="text-indigo-400 flex-shrink-0" />
            )}
          </div>
          <p className="text-sm text-slate-400 truncate">{agent.function}</p>
          {agent.port > 0 && (
            <p className="text-xs text-slate-500 mt-1">Port: {agent.port}</p>
          )}
        </div>
      </div>
    </div>
  );
}
