import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Interfaces para la administración de solicitudes de registro
export interface RegistrationRequestAdmin {
  id: string;
  tenant_id: string;
  community_id: string;
  email: string;
  full_name?: string;
  rut?: string;
  address?: string;
  phone_number?: string;
  email_notifications_enabled: boolean;
  whatsapp_notifications_enabled: boolean;
  provider: string;
  status: RegistrationRequestStatus;
  decided_by?: string;
  decided_at?: string;
  decision_notes?: string;
  created_at: string;
  updated_at: string;
  community?: {
    id: string;
    name: string;
  };
  attachments: RegistrationRequestAttachment[];
}

export interface RegistrationRequestAttachment {
  id: string;
  url: string;
  kind: AttachmentKind;
  created_at: string;
}

export enum RegistrationRequestStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED'
}

export enum AttachmentKind {
  ID_CARD_FRONT = 'id_card_front',
  ID_CARD_BACK = 'id_card_back',
  UTILITY_BILL = 'utility_bill',
  OTHER = 'other'
}

export interface RegistrationRequestListAdmin {
  requests: RegistrationRequestAdmin[];
  total: number;
}

export interface RegistrationDecision {
  decision_notes?: string;
}

export interface RegistrationStats {
  pending: number;
  approved: number;
  rejected: number;
  total: number;
  last_30_days: number;
}

@Injectable({ 
  providedIn: 'root' 
})
export class RegistrationAdminService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/registration';

  /**
   * Obtener solicitudes de registro para una comunidad específica
   */
  getRegistrationRequestsForCommunity(communityId: string): Observable<RegistrationRequestListAdmin> {
    return this.http.get<RegistrationRequestListAdmin>(`${this.baseUrl}/communities/${communityId}/requests`);
  }

  /**
   * Obtener detalles de una solicitud específica
   */
  getRegistrationRequestDetails(requestId: string): Observable<RegistrationRequestAdmin> {
    return this.http.get<RegistrationRequestAdmin>(`${this.baseUrl}/requests/${requestId}`);
  }

  /**
   * Aprobar una solicitud de registro
   */
  approveRegistrationRequest(requestId: string, decision: RegistrationDecision): Observable<RegistrationRequestAdmin> {
    return this.http.post<RegistrationRequestAdmin>(`${this.baseUrl}/requests/${requestId}/approve`, decision);
  }

  /**
   * Rechazar una solicitud de registro
   */
  rejectRegistrationRequest(requestId: string, decision: RegistrationDecision): Observable<RegistrationRequestAdmin> {
    return this.http.post<RegistrationRequestAdmin>(`${this.baseUrl}/requests/${requestId}/reject`, decision);
  }

  /**
   * Obtener estadísticas de solicitudes de registro
   */
  getRegistrationStats(): Observable<RegistrationStats> {
    // Nota: Este endpoint necesita ser implementado en el backend si no existe
    return this.http.get<RegistrationStats>(`${this.baseUrl}/stats`);
  }

  /**
   * Obtener todas las solicitudes de registro según permisos del usuario actual
   */
  getAllRegistrationRequests(filters?: {
    status?: RegistrationRequestStatus;
    search?: string;
    page?: number;
    per_page?: number;
  }): Observable<RegistrationRequestListAdmin> {
    let params = new URLSearchParams();

    if (filters?.status) params.set('status', filters.status);
    if (filters?.search) params.set('search', filters.search);
    if (filters?.page) params.set('page', filters.page.toString());
    if (filters?.per_page) params.set('per_page', filters.per_page.toString());

    const queryString = params.toString();
    const url = queryString ? `${this.baseUrl}/requests?${queryString}` : `${this.baseUrl}/requests`;

    return this.http.get<RegistrationRequestListAdmin>(url);
  }

  /**
   * Obtener URL para visualizar un archivo adjunto
   */
  getAttachmentUrl(attachmentUrl: string): string {
    console.log('🔍 getAttachmentUrl called with:', attachmentUrl);
    
    // Si la URL ya es completa, devolverla tal como está
    if (attachmentUrl.startsWith('http')) {
      console.log('🔍 URL is already complete:', attachmentUrl);
      return attachmentUrl;
    }

    // Si es una ruta relativa, construir la URL completa
    // Usar /files para que el proxy lo redirija al backend en puerto 8000
    const cleanUrl = attachmentUrl.startsWith('/') ? attachmentUrl.substring(1) : attachmentUrl;
    const finalUrl = `/files/${cleanUrl}`;

    console.log('🔍 Constructed URL:', finalUrl);
    console.log('🔍 This should be proxied to: http://127.0.0.1:8000/files/' + cleanUrl);

    return finalUrl;
  }

  /**
   * Descargar un archivo adjunto
   */
  downloadAttachment(attachmentUrl: string): Observable<Blob> {
    const url = this.getAttachmentUrl(attachmentUrl);
    return this.http.get(url, { responseType: 'blob' });
  }

  /**
   * Obtener el nombre del tipo de archivo para mostrar
   */
  getAttachmentKindLabel(kind: AttachmentKind): string {
    const labels: Record<AttachmentKind, string> = {
      [AttachmentKind.ID_CARD_FRONT]: 'Carnet (Frontal)',
      [AttachmentKind.ID_CARD_BACK]: 'Carnet (Trasero)',
      [AttachmentKind.UTILITY_BILL]: 'Cuenta de Servicios',
      [AttachmentKind.OTHER]: 'Documento Adicional'
    };
    return labels[kind] || 'Documento';
  }

  /**
   * Obtener el color del badge según el estado
   */
  getStatusColor(status: RegistrationRequestStatus): string {
    const colors: Record<RegistrationRequestStatus, string> = {
      [RegistrationRequestStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
      [RegistrationRequestStatus.APPROVED]: 'bg-green-100 text-green-800',
      [RegistrationRequestStatus.REJECTED]: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Obtener el texto del estado en español
   */
  getStatusLabel(status: RegistrationRequestStatus): string {
    const labels: Record<RegistrationRequestStatus, string> = {
      [RegistrationRequestStatus.PENDING]: 'Pendiente',
      [RegistrationRequestStatus.APPROVED]: 'Aprobada',
      [RegistrationRequestStatus.REJECTED]: 'Rechazada'
    };
    return labels[status] || status;
  }

  /**
   * Formatear fecha para mostrar
   */
  formatDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('es-CL', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  }

  /**
   * Validar notas de decisión
   */
  validateDecisionNotes(notes: string, isRejection: boolean = false): { isValid: boolean; error?: string } {
    if (isRejection && (!notes || notes.trim().length < 10)) {
      return {
        isValid: false,
        error: 'Las notas de rechazo son obligatorias y deben tener al menos 10 caracteres'
      };
    }

    if (notes && notes.length > 500) {
      return {
        isValid: false,
        error: 'Las notas no pueden exceder 500 caracteres'
      };
    }

    return { isValid: true };
  }
}
