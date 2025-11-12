/**
 * Modelos TypeScript para Espacios y Reservas
 * Corresponden a los schemas de Pydantic del backend
 */

// ===============================
// ENUMS
// ===============================

export enum ReservationStatus {
  PENDING = 'PENDING',
  CONFIRMED = 'CONFIRMED',
  CANCELLED = 'CANCELLED'
}

// ===============================
// SPACE MODELS
// ===============================

export interface SpaceCreateDto {
  name: string;
  description?: string;
  capacity?: number;
  requires_approval?: boolean;
  rules_json?: {
    max_hours_daily?: number;
    max_hours_weekly?: number;
    min_duration_hours?: number;
    max_duration_hours?: number;
    advance_days_required?: number;
  };
}

export interface SpaceUpdateDto {
  name?: string;
  description?: string;
  capacity?: number;
  requires_approval?: boolean;
  rules_json?: {
    max_hours_daily?: number;
    max_hours_weekly?: number;
    min_duration_hours?: number;
    max_duration_hours?: number;
    advance_days_required?: number;
  };
}

export interface SpaceDto {
  id: string;
  community_id: string;
  name: string;
  description?: string;
  capacity?: number;
  requires_approval: boolean;
  rules_json?: {
    max_hours_daily?: number;
    max_hours_weekly?: number;
    min_duration_hours?: number;
    max_duration_hours?: number;
    advance_days_required?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface SpaceListDto {
  spaces: SpaceDto[];
  total: number;
  page: number;
  per_page: number;
}

// ===============================
// RESERVATION MODELS
// ===============================

export interface ReservationCreateDto {
  space_id: string;
  start_time: string; // ISO 8601 format
  end_time: string;   // ISO 8601 format
}

export interface ReservationUpdateDto {
  cancel_reason?: string;
}

export interface ReservationDto {
  id: string;
  space_id: string;
  requesting_user_id: string;
  start_time: string;
  end_time: string;
  status: ReservationStatus;
  canceled_at?: string;
  cancel_reason?: string;
  created_at: string;
  updated_at: string;
  // Campos adicionales del backend
  space_name?: string;
  user_email?: string;
}

export interface ReservationListDto {
  reservations: ReservationDto[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ReservationApprovalDto {
  status: 'CONFIRMED' | 'CANCELLED';
  cancel_reason?: string;
}

export interface AvailabilityCheckDto {
  space_id: string;
  start_time: string;
  end_time: string;
}

export interface AvailabilityResponseDto {
  is_available: boolean;
  message: string;
  conflicting_reservations?: ReservationDto[];
}

export interface ReservationCalendarDto {
  reservations: ReservationDto[];
  total: number;
}

// ===============================
// FILTER MODELS
// ===============================

export interface SpaceFilters {
  page?: number;
  per_page?: number;
  search?: string;
}

export interface ReservationFilters {
  status?: ReservationStatus | string;
  space_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}
