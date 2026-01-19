// LeverEdge Command Center - Agent Registry
import { Agent, Domain } from './types';

export const DOMAINS: Record<string, Domain> = {
  gaia: {
    id: 'gaia',
    name: 'GAIA',
    theme: 'Primordial Creation',
    color: '#8B4513',
    supervisor: 'GAIA',
    agents: ['GAIA']
  },
  pantheon: {
    id: 'pantheon',
    name: 'PANTHEON',
    theme: 'Mount Olympus',
    color: '#FFD700',
    supervisor: 'ATLAS',
    agents: ['ATLAS', 'HEPHAESTUS', 'CHRONOS', 'HADES', 'AEGIS', 'ATHENA', 'HERMES', 'ARGUS', 'CHIRON', 'SCHOLAR']
  },
  sentinels: {
    id: 'sentinels',
    name: 'SENTINELS',
    theme: 'Mythic Guardians',
    color: '#8B0000',
    supervisor: 'GRIFFIN',
    agents: ['GRIFFIN', 'CERBERUS', 'SPHINX']
  },
  shire: {
    id: 'shire',
    name: 'THE SHIRE',
    theme: 'LOTR Hobbit Comfort',
    color: '#228B22',
    supervisor: 'GANDALF',
    agents: ['GANDALF', 'ARAGORN', 'BOMBADIL', 'SAMWISE', 'ARWEN']
  },
  keep: {
    id: 'keep',
    name: 'THE KEEP',
    theme: 'Game of Thrones',
    color: '#2F4F4F',
    supervisor: 'TYRION',
    agents: ['TYRION', 'SAMWELL-TARLY', 'GENDRY', 'STANNIS', 'DAVOS', 'LITTLEFINGER', 'BRONN', 'RAVEN']
  },
  chancery: {
    id: 'chancery',
    name: 'CHANCERY',
    theme: 'Royal Court',
    color: '#800020',
    supervisor: 'MAGISTRATE',
    agents: ['MAGISTRATE', 'EXCHEQUER', 'MAGNUS']
  },
  alchemy: {
    id: 'alchemy',
    name: 'ALCHEMY',
    theme: 'Mystic Workshop',
    color: '#9B59B6',
    supervisor: 'CATALYST',
    agents: ['CATALYST', 'SAGA', 'PRISM', 'ELIXIR', 'RELIC']
  },
  'aria-sanctum': {
    id: 'aria-sanctum',
    name: 'ARIA SANCTUM',
    theme: 'Ethereal Intelligence',
    color: '#E8D5E8',
    supervisor: 'ARIA',
    agents: ['ARIA', 'ARIA-OMNISCIENCE', 'ARIA-REMINDERS', 'VARYS']
  }
};

export const AGENTS: Record<string, Agent> = {
  // GAIA
  'GAIA': { id: 'gaia', name: 'GAIA', port: 8000, domain: 'gaia', function: 'Emergency bootstrap', supervisor: true },

  // PANTHEON
  'ATLAS': { id: 'atlas', name: 'ATLAS', port: 8007, domain: 'pantheon', function: 'Master Orchestrator', supervisor: true, councilMember: true },
  'HEPHAESTUS': { id: 'hephaestus', name: 'HEPHAESTUS', port: 8011, domain: 'pantheon', function: 'Builder/Deployer', councilMember: true },
  'CHRONOS': { id: 'chronos', name: 'CHRONOS', port: 8010, domain: 'pantheon', function: 'Backup Manager' },
  'HADES': { id: 'hades', name: 'HADES', port: 8008, domain: 'pantheon', function: 'Rollback/Recovery' },
  'AEGIS': { id: 'aegis', name: 'AEGIS', port: 8015, domain: 'pantheon', function: 'Credential Vault' },
  'ATHENA': { id: 'athena', name: 'ATHENA', port: 8013, domain: 'pantheon', function: 'Planner/Documenter', councilMember: true },
  'HERMES': { id: 'hermes', name: 'HERMES', port: 8014, domain: 'pantheon', function: 'Messenger/Notifications' },
  'ARGUS': { id: 'argus', name: 'ARGUS', port: 8016, domain: 'pantheon', function: 'Monitor' },
  'CHIRON': { id: 'chiron', name: 'CHIRON', port: 8017, domain: 'pantheon', function: 'Elite Business Mentor', councilMember: true },
  'SCHOLAR': { id: 'scholar', name: 'SCHOLAR', port: 8018, domain: 'pantheon', function: 'Market Research', councilMember: true },

  // SENTINELS
  'GRIFFIN': { id: 'griffin', name: 'GRIFFIN', port: 8019, domain: 'sentinels', function: 'Perimeter Watch', supervisor: true },
  'CERBERUS': { id: 'cerberus', name: 'CERBERUS', port: 8020, domain: 'sentinels', function: 'Defense/Auth' },
  'SPHINX': { id: 'sphinx', name: 'SPHINX', port: 8021, domain: 'sentinels', function: 'Access Control' },

  // THE SHIRE
  'GANDALF': { id: 'gandalf', name: 'GANDALF', port: 8103, domain: 'shire', function: 'Learning/Wisdom', supervisor: true, councilMember: true },
  'ARAGORN': { id: 'aragorn', name: 'ARAGORN', port: 8110, domain: 'shire', function: 'Fitness' },
  'BOMBADIL': { id: 'bombadil', name: 'BOMBADIL', port: 8101, domain: 'shire', function: 'Nutrition' },
  'SAMWISE': { id: 'samwise', name: 'SAMWISE', port: 8102, domain: 'shire', function: 'Meal Planning' },
  'ARWEN': { id: 'arwen', name: 'ARWEN', port: 8104, domain: 'shire', function: 'Relationships' },

  // THE KEEP
  'TYRION': { id: 'tyrion', name: 'TYRION', port: 8200, domain: 'keep', function: 'Project Leadership', supervisor: true, councilMember: true },
  'SAMWELL-TARLY': { id: 'samwell-tarly', name: 'SAMWELL-TARLY', port: 8201, domain: 'keep', function: 'Knowledge Keeper' },
  'GENDRY': { id: 'gendry', name: 'GENDRY', port: 8202, domain: 'keep', function: 'Workflow Builder', councilMember: true },
  'STANNIS': { id: 'stannis', name: 'STANNIS', port: 8203, domain: 'keep', function: 'QA/Compliance' },
  'DAVOS': { id: 'davos', name: 'DAVOS', port: 8204, domain: 'keep', function: 'Business Advisor', councilMember: true },
  'LITTLEFINGER': { id: 'littlefinger', name: 'LITTLEFINGER', port: 8205, domain: 'keep', function: 'Finance', councilMember: true },
  'BRONN': { id: 'bronn', name: 'BRONN', port: 8206, domain: 'keep', function: 'Procurement' },
  'RAVEN': { id: 'raven', name: 'RAVEN', port: 8209, domain: 'keep', function: 'News/Intel' },

  // CHANCERY
  'MAGISTRATE': { id: 'magistrate', name: 'MAGISTRATE', port: 8210, domain: 'chancery', function: 'Legal Counsel', supervisor: true, councilMember: true },
  'EXCHEQUER': { id: 'exchequer', name: 'EXCHEQUER', port: 8211, domain: 'chancery', function: 'Tax & Wealth' },
  'MAGNUS': { id: 'magnus', name: 'MAGNUS', port: 8017, domain: 'chancery', function: 'Universal Project Master', councilMember: true },

  // ALCHEMY
  'CATALYST': { id: 'catalyst', name: 'CATALYST', port: 8030, domain: 'alchemy', function: 'Creative Director', supervisor: true, councilMember: true },
  'SAGA': { id: 'saga', name: 'SAGA', port: 8031, domain: 'alchemy', function: 'Writer', councilMember: true },
  'PRISM': { id: 'prism', name: 'PRISM', port: 8032, domain: 'alchemy', function: 'Visual Designer', councilMember: true },
  'ELIXIR': { id: 'elixir', name: 'ELIXIR', port: 8033, domain: 'alchemy', function: 'Media Producer', councilMember: true },
  'RELIC': { id: 'relic', name: 'RELIC', port: 8034, domain: 'alchemy', function: 'Reviewer' },

  // ARIA SANCTUM
  'ARIA': { id: 'aria', name: 'ARIA', port: 0, domain: 'aria-sanctum', function: 'Personal AI', supervisor: true },
  'ARIA-OMNISCIENCE': { id: 'aria-omniscience', name: 'ARIA-OMNISCIENCE', port: 8400, domain: 'aria-sanctum', function: 'System Awareness' },
  'ARIA-REMINDERS': { id: 'aria-reminders', name: 'ARIA-REMINDERS', port: 8111, domain: 'aria-sanctum', function: 'Proactive Notifications' },
  'VARYS': { id: 'varys', name: 'VARYS', port: 8112, domain: 'aria-sanctum', function: 'Master of Whispers', councilMember: true },

  // CONCLAVE
  'CONVENER': { id: 'convener', name: 'CONVENER', port: 8300, domain: 'conclave', function: 'Council Facilitator' },
  'SCRIBE': { id: 'scribe', name: 'SCRIBE', port: 8301, domain: 'conclave', function: 'Council Secretary' }
};

export const COUNCIL_MEMBERS = Object.values(AGENTS).filter(a => a.councilMember);
export const SUPERVISORS = Object.values(AGENTS).filter(a => a.supervisor);

export function getAgentsByDomain(domainId: string): Agent[] {
  const domain = DOMAINS[domainId];
  if (!domain) return [];
  return domain.agents.map(name => AGENTS[name]).filter(Boolean);
}

export function getDomainForAgent(agentName: string): Domain | undefined {
  const agent = AGENTS[agentName];
  if (!agent) return undefined;
  return DOMAINS[agent.domain];
}
