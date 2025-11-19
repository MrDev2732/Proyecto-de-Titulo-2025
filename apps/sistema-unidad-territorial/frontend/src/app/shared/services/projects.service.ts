import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ProjectAttachment {
  id: string;
  original_filename: string;
  mime_type: string;
  file_url: string;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  status: string;
  observations: string | null;
  community_id: string;
  requesting_user_id: string;
  created_at: string;
  updated_at: string;
  attachments: ProjectAttachment[];
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ProjectStatusUpdate {
  status: string;
  observations?: string;
}

export interface ProjectFilters {
  page?: number;
  per_page?: number;
  status_filter?: string;
}

@Injectable({ 
  providedIn: 'root' 
})
export class ProjectsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/projects';

  /**
   * Listar proyectos con filtros y paginación
   * Nota: Usar slash final para evitar redirects 307 que pierden el header Authorization
   */
  listProjects(filters: ProjectFilters = {}): Observable<ProjectListResponse> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }
    if (filters.status_filter) {
      params = params.set('status_filter', filters.status_filter);
    }

    return this.http.get<ProjectListResponse>(`${this.baseUrl}/`, { params });
  }

  /**
   * Listar mis propuestas de proyectos
   */
  listMyProposals(filters: ProjectFilters = {}): Observable<ProjectListResponse> {
    let params = new HttpParams();

    if (filters.page) {
      params = params.set('page', filters.page.toString());
    }
    if (filters.per_page) {
      params = params.set('per_page', filters.per_page.toString());
    }
    if (filters.status_filter) {
      params = params.set('status_filter', filters.status_filter);
    }

    return this.http.get<ProjectListResponse>(`${this.baseUrl}/my-proposals`, { params });
  }

  /**
   * Obtener detalle de un proyecto
   */
  getProject(projectId: string): Observable<Project> {
    return this.http.get<Project>(`${this.baseUrl}/${projectId}`);
  }

  /**
   * Actualizar estado de un proyecto (aprobar/rechazar)
   */
  updateProjectStatus(projectId: string, statusData: ProjectStatusUpdate): Observable<Project> {
    return this.http.patch<Project>(`${this.baseUrl}/${projectId}/status`, statusData);
  }
}
