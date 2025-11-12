import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { 
  SpaceCreateDto,
  SpaceUpdateDto,
  SpaceDto,
  SpaceListDto,
  SpaceFilters
} from '../models/spaces.models';

@Injectable({ 
  providedIn: 'root' 
})
export class SpacesService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/spaces';

  /**
   * Crear un nuevo espacio
   * Nota: Importante usar slash final para evitar redirects 307 que pierden el header Authorization
   */
  createSpace(space: SpaceCreateDto): Observable<SpaceDto> {
    return this.http.post<SpaceDto>(`${this.baseUrl}/`, space);
  }

  /**
   * Obtener todos los espacios de la comunidad del usuario
   */
  getMySpaces(filters: SpaceFilters = {}): Observable<SpaceListDto> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }

    return this.http.get<SpaceListDto>(`${this.baseUrl}/my-community`, { params });
  }

  /**
   * Obtener todos los espacios (sin filtro de comunidad)
   */
  getAllSpaces(filters: SpaceFilters = {}): Observable<SpaceListDto> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }
    if (filters.search) {
      params = params.set('search', filters.search);
    }

    return this.http.get<SpaceListDto>(`${this.baseUrl}/`, { params });
  }

  /**
   * Obtener detalles de un espacio específico
   */
  getSpace(id: string): Observable<SpaceDto> {
    return this.http.get<SpaceDto>(`${this.baseUrl}/${id}`);
  }

  /**
   * Actualizar un espacio
   */
  updateSpace(id: string, space: SpaceUpdateDto): Observable<SpaceDto> {
    return this.http.patch<SpaceDto>(`${this.baseUrl}/${id}`, space);
  }

  /**
   * Eliminar (soft delete) un espacio
   */
  deleteSpace(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
