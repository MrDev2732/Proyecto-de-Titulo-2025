import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService, Project } from '../../shared/services/projects.service';

@Component({
  selector: 'app-projects-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './projects-management.component.html',
  styleUrls: ['./projects-management.component.scss']
})
export class ProjectsManagementComponent implements OnInit {
  private readonly projectsService = inject(ProjectsService);

  // Estado del componente
  projects = signal<Project[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // Filtros
  statusFilter = signal<string>('');

  // Modales
  showDetailModal = signal<boolean>(false);
  showApproveModal = signal<boolean>(false);
  showRejectModal = signal<boolean>(false);

  // Proyecto seleccionado
  selectedProject = signal<Project | null>(null);
  processing = signal<boolean>(false);

  // Formulario de observaciones
  observations = '';

  // Paginación
  currentPage = signal<number>(1);
  totalPages = signal<number>(1);
  total = signal<number>(0);

  ngOnInit(): void {
    this.loadProjects();
  }

  /**
   * Cargar todos los proyectos
   */
  async loadProjects(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.successMessage.set(null);

    try {
      const response = await this.projectsService.listProjects({
        page: this.currentPage(),
        per_page: 20,
        status_filter: this.statusFilter() || undefined
      }).toPromise();

      if (response) {
        this.projects.set(response.projects);
        this.total.set(response.total);
        this.totalPages.set(response.total_pages);
      }
    } catch (err: any) {
      console.error('Error loading projects:', err);

      if (err.status === 403) {
        this.error.set('⛔ No tienes permisos para gestionar proyectos.');
      } else if (err.status === 401) {
        this.error.set('❌ No estás autenticado. Por favor, inicia sesión nuevamente.');
      } else {
        this.error.set(err.error?.detail || 'Error al cargar los proyectos');
      }
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Cambiar filtro de estado
   */
  async onStatusFilterChange(status: string): Promise<void> {
    this.statusFilter.set(status);
    this.currentPage.set(1);
    await this.loadProjects();
  }

  /**
   * Cambiar página
   */
  async goToPage(page: number): Promise<void> {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    await this.loadProjects();
  }

  /**
   * Abrir modal de detalle
   */
  openDetailModal(project: Project): void {
    this.selectedProject.set(project);
    this.showDetailModal.set(true);
  }

  /**
   * Abrir modal de aprobación
   */
  openApproveModal(project: Project): void {
    this.selectedProject.set(project);
    this.observations = '';
    this.showApproveModal.set(true);
  }

  /**
   * Abrir modal de rechazo
   */
  openRejectModal(project: Project): void {
    this.selectedProject.set(project);
    this.observations = '';
    this.showRejectModal.set(true);
  }

  /**
   * Cerrar todos los modales
   */
  closeModals(): void {
    this.showDetailModal.set(false);
    this.showApproveModal.set(false);
    this.showRejectModal.set(false);
    this.selectedProject.set(null);
    this.observations = '';
  }

  /**
   * Aprobar proyecto
   */
  async approveProject(): Promise<void> {
    const selected = this.selectedProject();
    if (!selected) return;

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.projectsService.updateProjectStatus(selected.id, {
        status: 'IN_PROGRESS',
        observations: this.observations || undefined
      }).toPromise();

      this.successMessage.set('✅ Proyecto aprobado exitosamente');
      this.closeModals();
      await this.loadProjects();

      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error approving project:', err);
      this.error.set(err.error?.detail || 'Error al aprobar el proyecto');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Rechazar proyecto
   */
  async rejectProject(): Promise<void> {
    const selected = this.selectedProject();
    if (!selected) return;

    if (!this.observations.trim()) {
      this.error.set('Debes proporcionar una razón para el rechazo');
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.projectsService.updateProjectStatus(selected.id, {
        status: 'REJECTED',
        observations: this.observations
      }).toPromise();

      this.successMessage.set('✅ Proyecto rechazado');
      this.closeModals();
      await this.loadProjects();

      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error rejecting project:', err);
      this.error.set(err.error?.detail || 'Error al rechazar el proyecto');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Marcar proyecto como completado
   */
  async completeProject(project: Project): Promise<void> {
    this.processing.set(true);
    this.error.set(null);

    try {
      await this.projectsService.updateProjectStatus(project.id, {
        status: 'COMPLETED'
      }).toPromise();

      this.successMessage.set('✅ Proyecto marcado como completado');
      await this.loadProjects();

      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error completing project:', err);
      this.error.set(err.error?.detail || 'Error al completar el proyecto');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Formatear fecha
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-CL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  /**
   * Obtener clase de badge según estado
   */
  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800';
      case 'IN_PROGRESS':
        return 'bg-blue-100 text-blue-800';
      case 'COMPLETED':
        return 'bg-green-100 text-green-800';
      case 'REJECTED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  /**
   * Obtener texto de badge según estado
   */
  getStatusBadgeText(status: string): string {
    switch (status) {
      case 'PENDING':
        return 'Pendiente';
      case 'IN_PROGRESS':
        return 'En Progreso';
      case 'COMPLETED':
        return 'Completado';
      case 'REJECTED':
        return 'Rechazado';
      default:
        return status;
    }
  }

  /**
   * Truncar texto
   */
  truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }
}
