'use client';

import { notFound } from 'next/navigation';
import Link from 'next/link';
import { AGENTS, DOMAINS, getDomainForAgent } from '@/lib/agents';
import { MetricCard } from '@/components/dashboard/MetricCard';
import {
  ArrowLeft, Shield, MessageSquare, Zap, Terminal,
  Activity, Clock, Settings, Play, RefreshCw, AlertTriangle
} from 'lucide-react';

interface AgentPageProps {
  params: { agent: string };
}

export default function AgentPage({ params }: AgentPageProps) {
  const agentId = params.agent;

  // Find agent by ID (lowercase)
  const agent = Object.values(AGENTS).find(a => a.id === agentId);

  if (!agent) {
    notFound();
  }

  const domain = getDomainForAgent(agent.name);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={domain ? `/domains/${domain.id}` : '/'}
          className="p-2 hover:bg-slate-800 rounded-lg transition"
        >
          <ArrowLeft size={20} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold" style={{ color: domain?.color || '#60A5FA' }}>
              {agent.name}
            </h1>
            {agent.supervisor && (
              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full flex items-center gap-1">
                <Shield size={12} />
                Supervisor
              </span>
            )}
            {agent.councilMember && (
              <span className="px-2 py-1 bg-indigo-500/20 text-indigo-400 text-xs rounded-full flex items-center gap-1">
                <MessageSquare size={12} />
                Council
              </span>
            )}
          </div>
          <p className="text-slate-400">{agent.function}</p>
          {domain && (
            <Link
              href={`/domains/${domain.id}`}
              className="text-sm hover:underline"
              style={{ color: domain.color }}
            >
              {domain.name} Domain
            </Link>
          )}
        </div>
      </div>

      {/* Agent Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Status"
          value="Online"
          subtitle="Healthy"
          icon={<Activity size={20} />}
          color="#34D399"
        />
        <MetricCard
          title="Port"
          value={agent.port > 0 ? agent.port.toString() : 'N/A'}
          subtitle={agent.port > 0 ? 'HTTP API' : 'No direct port'}
          icon={<Terminal size={20} />}
          color="#60A5FA"
        />
        <MetricCard
          title="Uptime"
          value="99.9%"
          subtitle="Last 30 days"
          icon={<Clock size={20} />}
          color="#FBBF24"
        />
        <MetricCard
          title="Last Active"
          value="Just now"
          subtitle="Recent activity"
          icon={<Zap size={20} />}
          color="#A78BFA"
        />
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-4">
        {agent.port > 0 && (
          <>
            <button className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg transition">
              <Play size={18} />
              <span>Execute Task</span>
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
              <RefreshCw size={18} />
              <span>Restart Agent</span>
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
              <Terminal size={18} />
              <span>View Logs</span>
            </button>
          </>
        )}
        {agent.councilMember && (
          <Link
            href={`/council/new?summon=${agent.name}`}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg transition"
          >
            <MessageSquare size={18} />
            <span>Summon to Council</span>
          </Link>
        )}
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition">
          <Settings size={18} />
          <span>Configure</span>
        </button>
      </div>

      {/* Agent Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Info Panel */}
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Terminal size={18} />
            Agent Details
          </h3>
          <div className="space-y-3">
            <DetailRow label="ID" value={agent.id} />
            <DetailRow label="Name" value={agent.name} />
            <DetailRow label="Function" value={agent.function} />
            <DetailRow label="Domain" value={domain?.name || 'Unknown'} />
            <DetailRow label="Port" value={agent.port > 0 ? agent.port.toString() : 'None'} />
            <DetailRow label="Supervisor" value={agent.supervisor ? 'Yes' : 'No'} />
            <DetailRow label="Council Member" value={agent.councilMember ? 'Yes' : 'No'} />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity size={18} />
            Recent Activity
          </h3>
          <div className="space-y-2 text-sm">
            <ActivityRow time="Just now" event="Health check passed" status="success" />
            <ActivityRow time="5m ago" event="Task executed successfully" status="success" />
            <ActivityRow time="1h ago" event="Configuration updated" status="info" />
            <ActivityRow time="2h ago" event="Restarted by ATLAS" status="info" />
          </div>
        </div>
      </div>

      {/* API Endpoints (if port available) */}
      {agent.port > 0 && (
        <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap size={18} />
            API Endpoints
          </h3>
          <div className="space-y-2">
            <EndpointRow method="GET" path={`http://localhost:${agent.port}/health`} description="Health check" />
            <EndpointRow method="GET" path={`http://localhost:${agent.port}/`} description="Root endpoint" />
            <EndpointRow method="POST" path={`http://localhost:${agent.port}/execute`} description="Execute task" />
          </div>
        </div>
      )}

      {/* Alerts Section */}
      <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle size={18} className="text-amber-400" />
          Alerts & Warnings
        </h3>
        <div className="text-sm text-slate-400">
          No active alerts for this agent.
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-700 last:border-0">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function ActivityRow({ time, event, status }: { time: string; event: string; status: 'success' | 'error' | 'info' }) {
  const statusColors = {
    success: 'text-green-400',
    error: 'text-red-400',
    info: 'text-blue-400'
  };

  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className="text-xs text-slate-500 w-16 flex-shrink-0">{time}</span>
      <span className={`flex-1 ${statusColors[status]}`}>{event}</span>
    </div>
  );
}

function EndpointRow({ method, path, description }: { method: string; path: string; description: string }) {
  const methodColors: Record<string, string> = {
    GET: 'bg-green-500/20 text-green-400',
    POST: 'bg-blue-500/20 text-blue-400',
    PUT: 'bg-amber-500/20 text-amber-400',
    DELETE: 'bg-red-500/20 text-red-400'
  };

  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-700 last:border-0">
      <span className={`px-2 py-0.5 rounded text-xs font-mono ${methodColors[method] || 'bg-slate-700'}`}>
        {method}
      </span>
      <code className="text-sm text-slate-300 flex-1 truncate">{path}</code>
      <span className="text-xs text-slate-500">{description}</span>
    </div>
  );
}
