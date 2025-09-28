import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { 
  RegistrationRequestDto, 
  RegistrationRequestListDto, 
  RegistrationDecisionRequestDto,
  RegistrationRequestFilters 
} from '../models/registration-request.models';

@Injectable({ 
  providedIn: 'root' 
})
export class RegistrationRequestService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/admin/registration-requests';

  /**
   * Obtener lista de solicitudes de registro con filtros
   */
  getRegistrationRequests(filters: RegistrationRequestFilters = {}): Observable<RegistrationRequestListDto> {
    let params = new HttpParams();

    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.provider) {
      params = params.set('provider', filters.provider);
    }
    if (filters.community_id) {
      params = params.set('community_id', filters.community_id);
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }
    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }

    return this.http.get<RegistrationRequestListDto>(this.baseUrl, { params });
  }

  /**
   * Obtener detalles de una solicitud específica
   */
  getRegistrationRequest(id: string): Observable<RegistrationRequestDto> {
    return this.http.get<RegistrationRequestDto>(`${this.baseUrl}/${id}`);
  }

  /**
   * Aprobar o rechazar una solicitud de registro
   */
  processRegistrationRequest(
    id: string, 
    decision: RegistrationDecisionRequestDto
  ): Observable<RegistrationRequestDto> {
    return this.http.patch<RegistrationRequestDto>(`${this.baseUrl}/${id}/process`, decision);
  }

  /**
   * Obtener estadísticas de solicitudes de registro
   */
  getRegistrationStats(): Observable<{
    pending: number;
    approved: number;
    rejected: number;
    total: number;
    last_30_days: number;
  }> {
    return this.http.get<{
      pending: number;
      approved: number;
      rejected: number;
      total: number;
      last_30_days: number;
    }>(`${this.baseUrl}/stats`);
  }
}
