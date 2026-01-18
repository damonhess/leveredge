import { Agent } from '@/lib/types';
import { Circle } from 'lucide-react';

interface AgentStatusProps {
  agent: Agent;
  onClick?: () => void;
}

export function AgentStatus({ agent, onClick }: AgentStatusProps) {
  const statusColors = {
    online: 'text-green-400',
    offline: 'text-red-400',
    degraded: 'text-amber-400'
  };

  const status = agent.status || 'offline';

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition w-full text-left"
    >
      <Circle
        size={8}
        className={`fill-current ${statusColors[status]}`}
      />
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{agent.name}</p>
        <p className="text-xs text-slate-400 truncate">{agent.function}</p>
      </div>
      {agent.port > 0 && (
        <span className="text-xs text-slate-500">:{agent.port}</span>
      )}
    </button>
  );
}
