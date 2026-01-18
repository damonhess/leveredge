// LeverEdge Command Center - TypeScript Types

export interface Agent {
  id: string;
  name: string;
  port: number;
  domain: string;
  function: string;
  supervisor?: boolean;
  councilMember?: boolean;
  status?: 'online' | 'offline' | 'degraded';
}

export interface Domain {
  id: string;
  name: string;
  theme: string;
  color: string;
  supervisor: string;
  agents: string[];
}

export interface Meeting {
  id: string;
  title: string;
  topic: string;
  status: 'CONVENED' | 'IN_SESSION' | 'VOTING' | 'ADJOURNED';
  participants: string[];
  transcript: TranscriptEntry[];
  decisions: Decision[];
  actions: ActionItem[];
  created_at: string;
  started_at?: string;
  ended_at?: string;
}

export interface TranscriptEntry {
  speaker: string;
  message: string;
  message_type: string;
  timestamp: string;
  sequence_num: number;
}

export interface Decision {
  id: string;
  decision: string;
  proposed_by: string;
  status: string;
  rationale?: string;
}

export interface ActionItem {
  id: string;
  action: string;
  assigned_to: string;
  due_date?: string;
  status: string;
}

export interface VoteResult {
  question: string;
  options: string[];
  results: Record<string, {
    count: number;
    voters: {
      agent: string;
      position: string;
      reasoning: string;
      confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    }[];
  }>;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'unknown';
  message?: string;
}

export interface SystemHealthStatus {
  agents: Record<string, string>;
  online: number;
  total: number;
}

export interface Metrics {
  agentsOnline: number;
  portfolioValue: string;
  daysToLaunch: number;
  councilMembers: number;
}
