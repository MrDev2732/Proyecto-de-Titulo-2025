export interface RegistrationRequestDto {
  id: string;
  tenant_id: string;
  community_id: string;
  email: string;
  full_name?: string;
  rut?: string;
  address?: string;
  provider: RegistrationProvider;
  status: RegistrationStatus;
  decided_by?: string;
  decided_at?: string;
  decision_notes?: string;
  created_at: string;
  updated_at: string;
  community?: {
    id: string;
    name: string;
  };
}

export interface RegistrationDecisionRequestDto {
  decision: RegistrationStatus.APPROVED | RegistrationStatus.REJECTED;
  decision_notes?: string;
}

export interface RegistrationRequestListDto {
  requests: RegistrationRequestDto[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export enum RegistrationProvider {
  EMAIL = 'EMAIL',
  GOOGLE = 'GOOGLE'
}

export enum RegistrationStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED'
}

export interface RegistrationRequestFilters {
  status?: RegistrationStatus;
  provider?: RegistrationProvider;
  community_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
}
