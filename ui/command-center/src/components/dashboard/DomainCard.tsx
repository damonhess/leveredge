import Link from 'next/link';
import { Domain } from '@/lib/types';
import { ChevronRight } from 'lucide-react';

interface DomainCardProps {
  domain: Domain;
}

export function DomainCard({ domain }: DomainCardProps) {
  const agentCount = domain.agents.length;

  return (
    <Link
      href={`/domains/${domain.id}`}
      className="block bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition group"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold" style={{ color: domain.color }}>
            {domain.name}
          </h3>
          <p className="text-sm text-slate-400 mt-1">{domain.theme}</p>
        </div>
        <ChevronRight
          size={20}
          className="text-slate-600 group-hover:text-slate-400 transition"
        />
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-400">
          {agentCount} agent{agentCount !== 1 ? 's' : ''}
        </span>
        <span className="text-slate-500">
          {domain.supervisor}
        </span>
      </div>

      <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: '100%',
            backgroundColor: domain.color,
            opacity: 0.7
          }}
        />
      </div>
    </Link>
  );
}
