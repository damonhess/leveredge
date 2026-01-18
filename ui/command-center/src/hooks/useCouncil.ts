// Council-related React Query hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Meeting, TranscriptEntry, Decision, VoteResult } from '@/lib/types';

// Query Keys
export const councilKeys = {
  all: ['council'] as const,
  meetings: () => [...councilKeys.all, 'meetings'] as const,
  meeting: (id: string) => [...councilKeys.all, 'meeting', id] as const,
  transcript: (id: string) => [...councilKeys.all, 'transcript', id] as const,
  active: () => [...councilKeys.all, 'active'] as const,
};

// Types
interface ConveneMeetingParams {
  topic: string;
  attendees: string[];
  options?: {
    enableVoting?: boolean;
    recordTranscript?: boolean;
    requireUnanimous?: boolean;
  };
}

interface SpeakParams {
  meetingId: string;
  speaker: string;
  message: string;
}

interface SummonParams {
  meetingId: string;
  agentName: string;
  reason?: string;
}

interface VoteParams {
  meetingId: string;
  motion: string;
}

// Fetch all meetings
export function useMeetings() {
  return useQuery({
    queryKey: councilKeys.meetings(),
    queryFn: async () => {
      const { data } = await api.get<Meeting[]>('/meetings');
      return data;
    },
  });
}

// Fetch single meeting
export function useMeeting(meetingId: string) {
  return useQuery({
    queryKey: councilKeys.meeting(meetingId),
    queryFn: async () => {
      const { data } = await api.get<Meeting>(`/meeting/${meetingId}`);
      return data;
    },
    enabled: !!meetingId,
    refetchInterval: 5000, // Poll every 5 seconds for active meetings
  });
}

// Fetch meeting transcript
export function useTranscript(meetingId: string) {
  return useQuery({
    queryKey: councilKeys.transcript(meetingId),
    queryFn: async () => {
      const { data } = await api.get<TranscriptEntry[]>(`/transcript/${meetingId}`);
      return data;
    },
    enabled: !!meetingId,
    refetchInterval: 3000, // Poll every 3 seconds for new entries
  });
}

// Fetch active meetings
export function useActiveMeetings() {
  return useQuery({
    queryKey: councilKeys.active(),
    queryFn: async () => {
      const { data } = await api.get<Meeting[]>('/meetings/active');
      return data;
    },
    refetchInterval: 10000,
  });
}

// Convene new meeting
export function useConveneMeeting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: ConveneMeetingParams) => {
      const { data } = await api.post<Meeting>('/convene', params);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: councilKeys.meetings() });
      queryClient.invalidateQueries({ queryKey: councilKeys.active() });
    },
  });
}

// Speak in meeting
export function useSpeak() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: SpeakParams) => {
      const { data } = await api.post(`/speak`, params);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: councilKeys.transcript(variables.meetingId) });
      queryClient.invalidateQueries({ queryKey: councilKeys.meeting(variables.meetingId) });
    },
  });
}

// Request floor
export function useRequestFloor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ meetingId, agentName }: { meetingId: string; agentName: string }) => {
      const { data } = await api.post(`/request-floor`, { meetingId, agentName });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: councilKeys.meeting(variables.meetingId) });
    },
  });
}

// Yield floor
export function useYieldFloor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ meetingId }: { meetingId: string }) => {
      const { data } = await api.post(`/next`, { meetingId });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: councilKeys.meeting(variables.meetingId) });
    },
  });
}

// Summon agent
export function useSummon() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: SummonParams) => {
      const { data } = await api.post(`/summon`, params);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: councilKeys.meeting(variables.meetingId) });
    },
  });
}

// Call vote
export function useCallVote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: VoteParams) => {
      const { data } = await api.post<VoteResult>(`/vote`, params);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: councilKeys.meeting(variables.meetingId) });
      queryClient.invalidateQueries({ queryKey: councilKeys.transcript(variables.meetingId) });
    },
  });
}

// Adjourn meeting
export function useAdjourn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ meetingId, summary }: { meetingId: string; summary?: string }) => {
      const { data } = await api.post(`/adjourn-v2`, { meetingId, summary });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: councilKeys.all });
    },
  });
}
