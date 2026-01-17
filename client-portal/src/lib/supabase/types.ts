export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      clients: {
        Row: {
          id: string
          name: string
          email: string
          company: string | null
          created_at: string
        }
        Insert: {
          id?: string
          name: string
          email: string
          company?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          name?: string
          email?: string
          company?: string | null
          created_at?: string
        }
      }
      projects: {
        Row: {
          id: string
          client_id: string
          name: string
          status: string
          created_at: string
        }
        Insert: {
          id?: string
          client_id: string
          name: string
          status?: string
          created_at?: string
        }
        Update: {
          id?: string
          client_id?: string
          name?: string
          status?: string
          created_at?: string
        }
      }
      invoices: {
        Row: {
          id: string
          client_id: string
          amount: number
          status: string
          due_date: string
        }
        Insert: {
          id?: string
          client_id: string
          amount: number
          status?: string
          due_date: string
        }
        Update: {
          id?: string
          client_id?: string
          amount?: number
          status?: string
          due_date?: string
        }
      }
      support_tickets: {
        Row: {
          id: string
          client_id: string
          subject: string
          message: string
          status: string
          created_at: string
        }
        Insert: {
          id?: string
          client_id: string
          subject: string
          message: string
          status?: string
          created_at?: string
        }
        Update: {
          id?: string
          client_id?: string
          subject?: string
          message?: string
          status?: string
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}

// Helper types for easier usage
export type Client = Database['public']['Tables']['clients']['Row']
export type Project = Database['public']['Tables']['projects']['Row']
export type Invoice = Database['public']['Tables']['invoices']['Row']
export type SupportTicket = Database['public']['Tables']['support_tickets']['Row']
