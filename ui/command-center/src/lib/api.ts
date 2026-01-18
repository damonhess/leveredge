// LeverEdge Command Center - API Client
import axios from 'axios';

// Default to CONVENER for council operations, ATLAS for orchestration
const CONVENER_URL = process.env.NEXT_PUBLIC_CONVENER_URL || 'http://localhost:8300';
const ATLAS_URL = process.env.NEXT_PUBLIC_ATLAS_URL || 'http://localhost:8007';

export const api = axios.create({
  baseURL: CONVENER_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const atlasApi = axios.create({
  baseURL: ATLAS_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add interceptors for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('CONVENER API Error:', error.message);
    return Promise.reject(error);
  }
);

atlasApi.interceptors.response.use(
  response => response,
  error => {
    console.error('ATLAS API Error:', error.message);
    return Promise.reject(error);
  }
);

// Helper to check agent health
export async function checkAgentHealth(port: number): Promise<boolean> {
  try {
    const response = await axios.get(`http://localhost:${port}/health`, { timeout: 2000 });
    return response.status === 200;
  } catch {
    return false;
  }
}
