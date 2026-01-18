// Agent-related React Query hooks
import { useQuery, useMutation } from '@tanstack/react-query';
import { atlasApi, checkAgentHealth } from '@/lib/api';
import { AGENTS } from '@/lib/agents';
import { HealthStatus } from '@/lib/types';

// Query Keys
export const agentKeys = {
  all: ['agents'] as const,
  health: () => [...agentKeys.all, 'health'] as const,
  agentHealth: (id: string) => [...agentKeys.all, 'health', id] as const,
  status: () => [...agentKeys.all, 'status'] as const,
};

// Types
interface AgentHealthResult {
  agentId: string;
  name: string;
  port: number;
  healthy: boolean;
  lastChecked: Date;
}

// Check health of all agents
export function useAllAgentHealth() {
  return useQuery({
    queryKey: agentKeys.health(),
    queryFn: async (): Promise<AgentHealthResult[]> => {
      const agents = Object.values(AGENTS).filter(a => a.port > 0);

      const results = await Promise.all(
        agents.map(async (agent) => {
          const healthy = await checkAgentHealth(agent.port);
          return {
            agentId: agent.id,
            name: agent.name,
            port: agent.port,
            healthy,
            lastChecked: new Date(),
          };
        })
      );

      return results;
    },
    refetchInterval: 30000, // Check every 30 seconds
    staleTime: 15000,
  });
}

// Check health of single agent
export function useAgentHealth(agentId: string) {
  const agent = Object.values(AGENTS).find(a => a.id === agentId);

  return useQuery({
    queryKey: agentKeys.agentHealth(agentId),
    queryFn: async (): Promise<HealthStatus> => {
      if (!agent || agent.port === 0) {
        return { status: 'unknown', message: 'No port configured' };
      }

      const healthy = await checkAgentHealth(agent.port);
      return {
        status: healthy ? 'healthy' : 'unhealthy',
        message: healthy ? 'Agent responding' : 'Agent not responding',
      };
    },
    enabled: !!agent,
    refetchInterval: 10000,
  });
}

// Get system status from ATLAS
export function useSystemStatus() {
  return useQuery({
    queryKey: agentKeys.status(),
    queryFn: async () => {
      const { data } = await atlasApi.get('/status');
      return data;
    },
    refetchInterval: 60000,
  });
}

// Execute task on agent
export function useExecuteTask() {
  return useMutation({
    mutationFn: async ({ agentId, task }: { agentId: string; task: string }) => {
      const agent = Object.values(AGENTS).find(a => a.id === agentId);
      if (!agent || agent.port === 0) {
        throw new Error('Agent not found or no port configured');
      }

      const { data } = await atlasApi.post(`/execute`, {
        target: agent.name,
        task,
      });
      return data;
    },
  });
}

// Restart agent via ATLAS
export function useRestartAgent() {
  return useMutation({
    mutationFn: async ({ agentId }: { agentId: string }) => {
      const agent = Object.values(AGENTS).find(a => a.id === agentId);
      if (!agent) {
        throw new Error('Agent not found');
      }

      const { data } = await atlasApi.post(`/restart`, {
        agent: agent.name,
      });
      return data;
    },
  });
}
