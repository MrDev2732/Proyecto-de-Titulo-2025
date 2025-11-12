import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { 
  ReservationCreateDto,
  ReservationUpdateDto,
  ReservationDto,
  ReservationListDto,
  ReservationApprovalDto,
  AvailabilityCheckDto,
  AvailabilityResponseDto,
  ReservationCalendarDto,
  ReservationFilters
} from '../models/spaces.models';

@Injectable({ 
  providedIn: 'root' 
})
export class ReservationsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/reservations';

  /**
   * Verificar disponibilidad de un espacio
   */
  checkAvailability(check: AvailabilityCheckDto): Observable<AvailabilityResponseDto> {
    return this.http.post<AvailabilityResponseDto>(`${this.baseUrl}/availability`, check);
  }

  /**
   * Crear una nueva reserva
   */
  createReservation(reservation: ReservationCreateDto): Observable<ReservationDto> {
    return this.http.post<ReservationDto>(`${this.baseUrl}/`, reservation);
  }

  /**
   * Obtener las reservas del usuario actual
   */
  getMyReservations(filters: ReservationFilters = {}): Observable<ReservationListDto> {
    let params = new HttpParams();

    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.start_date) {
      params = params.set('start_date', filters.start_date);
    }
    if (filters.end_date) {
      params = params.set('end_date', filters.end_date);
    }
    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }

    return this.http.get<ReservationListDto>(`${this.baseUrl}/my-reservations`, { params });
  }

  /**
   * Obtener las reservas de la comunidad (requiere permisos)
   */
  getCommunityReservations(filters: ReservationFilters = {}): Observable<ReservationListDto> {
    let params = new HttpParams();

    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.start_date) {
      params = params.set('start_date', filters.start_date);
    }
    if (filters.end_date) {
      params = params.set('end_date', filters.end_date);
    }
    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }

    return this.http.get<ReservationListDto>(`${this.baseUrl}/community`, { params });
  }

  /**
   * Obtener vista de calendario de reservas de un espacio
   */
  getSpaceCalendar(spaceId: string, startDate: string, endDate: string): Observable<ReservationCalendarDto> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);

    return this.http.get<ReservationCalendarDto>(`${this.baseUrl}/calendar/${spaceId}`, { params });
  }

  /**
   * Aprobar o rechazar una reserva (solo administradores)
   */
  approveReservation(id: string, approval: ReservationApprovalDto): Observable<ReservationDto> {
    return this.http.patch<ReservationDto>(`${this.baseUrl}/${id}/approve`, approval);
  }

  /**
   * Cancelar una reserva propia
   */
  cancelReservation(id: string, cancelReason?: string): Observable<ReservationDto> {
    const body: ReservationUpdateDto = { cancel_reason: cancelReason };
    return this.http.patch<ReservationDto>(`${this.baseUrl}/${id}/cancel`, body);
  }

  /**
   * Obtener detalles de una reserva específica
   */
  getReservation(id: string): Observable<ReservationDto> {
    return this.http.get<ReservationDto>(`${this.baseUrl}/${id}`);
  }
}
