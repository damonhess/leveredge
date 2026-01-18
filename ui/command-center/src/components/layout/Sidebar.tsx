'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { DOMAINS } from '@/lib/agents';
import {
  Home, Shield, Leaf, Sword, Scale,
  Sparkles, Star, MessageSquare, Settings,
  Globe, Crown
} from 'lucide-react';

const domainIcons: Record<string, React.ElementType> = {
  gaia: Globe,
  pantheon: Crown,
  sentinels: Shield,
  shire: Leaf,
  keep: Sword,
  chancery: Scale,
  alchemy: Sparkles,
  'aria-sanctum': Star,
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold">LeverEdge</h1>
        <p className="text-xs text-slate-400">Command Center</p>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        <Link
          href="/"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
            pathname === '/' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          <Home size={18} />
          <span>Hub</span>
        </Link>

        <div className="pt-4 pb-2 px-3 text-xs text-slate-500 uppercase tracking-wider">
          Domains
        </div>

        {Object.values(DOMAINS).map(domain => {
          const Icon = domainIcons[domain.id] || Star;
          const isActive = pathname.startsWith(`/domains/${domain.id}`);

          return (
            <Link
              key={domain.id}
              href={`/domains/${domain.id}`}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <Icon size={18} style={{ color: domain.color }} />
              <span>{domain.name}</span>
            </Link>
          );
        })}

        <div className="pt-4 pb-2 px-3 text-xs text-slate-500 uppercase tracking-wider">
          Council
        </div>

        <Link
          href="/council"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
            pathname.startsWith('/council') ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          <MessageSquare size={18} />
          <span>The Conclave</span>
        </Link>
      </nav>

      <div className="p-4 border-t border-slate-700">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-lg transition hover:bg-slate-700/50"
        >
          <Settings size={18} />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
