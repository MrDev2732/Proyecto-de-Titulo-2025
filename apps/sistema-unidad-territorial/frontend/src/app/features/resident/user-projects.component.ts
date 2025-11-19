import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ProjectsService, Project, ProjectListResponse } from '../../shared/services/projects.service';

@Component({
  selector: 'app-user-projects',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './user-projects.component.html',
  styleUrls: ['./user-projects.component.scss']
})
export class UserProjectsComponent implements OnInit {
  private readonly projectsService = inject(ProjectsService);
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);

  // Signals
  projects = signal<Project[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  currentPage = signal<number>(1);
  totalPages = signal<number>(1);
  selectedStatusFilter = signal<string>('');

  // Modal states
  showCreateModal = signal<boolean>(false);
  showDetailModal = signal<boolean>(false);
  selectedProject = signal<Project | null>(null);
  submitting = signal<boolean>(false);

  // Form data
  formData = signal({
    title: '',
    description: '',
    attachments: [] as File[]
  });

  // Form errors
  formErrors = signal({
    title: '',
    description: '',
    attachments: ''
  });

  ngOnInit(): void {
    this.loadProjects();
  }

  async loadProjects(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);

    try {
      const response = await this.projectsService.listMyProposals({
        page: this.currentPage(),
        per_page: 10,
        status_filter: this.selectedStatusFilter() || undefined
      }).toPromise();

      if (response) {
        this.projects.set(response.projects);
        this.totalPages.set(response.total_pages);
      }
    } catch (err: any) {
      console.error('Error loading projects:', err);
      this.error.set('Error al cargar tus propuestas. Por favor, inténtalo nuevamente.');
    } finally {
      this.loading.set(false);
    }
  }

  async changePage(page: number): Promise<void> {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      await this.loadProjects();
    }
  }

  async applyStatusFilter(status: string): Promise<void> {
    this.selectedStatusFilter.set(status);
    this.currentPage.set(1);
    await this.loadProjects();
  }

  openCreateModal(): void {
    this.resetForm();
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
    this.resetForm();
  }

  openDetailModal(project: Project): void {
    this.selectedProject.set(project);
    this.showDetailModal.set(true);
  }

  closeDetailModal(): void {
    this.showDetailModal.set(false);
    this.selectedProject.set(null);
  }

  resetForm(): void {
    this.formData.set({
      title: '',
      description: '',
      attachments: []
    });
    this.formErrors.set({
      title: '',
      description: '',
      attachments: ''
    });
  }

  onFilesSelected(event: any): void {
    const files: FileList = event.target.files;
    if (files && files.length > 0) {
      const fileArray = Array.from(files);
      this.formData.update(data => ({
        ...data,
        attachments: fileArray
      }));
    }
  }

  removeFile(index: number): void {
    this.formData.update(data => ({
      ...data,
      attachments: data.attachments.filter((_, i) => i !== index)
    }));
  }

  validateForm(): boolean {
    const errors = {
      title: '',
      description: '',
      attachments: ''
    };

    let isValid = true;

    if (!this.formData().title.trim()) {
      errors.title = 'El título es requerido';
      isValid = false;
    } else if (this.formData().title.trim().length < 5) {
      errors.title = 'El título debe tener al menos 5 caracteres';
      isValid = false;
    } else if (this.formData().title.trim().length > 200) {
      errors.title = 'El título no puede exceder 200 caracteres';
      isValid = false;
    }

    if (!this.formData().description.trim()) {
      errors.description = 'La descripción es requerida';
      isValid = false;
    } else if (this.formData().description.trim().length < 20) {
      errors.description = 'La descripción debe tener al menos 20 caracteres';
      isValid = false;
    }

    this.formErrors.set(errors);
    return isValid;
  }

  async submitProject(): Promise<void> {
    if (!this.validateForm()) {
      return;
    }

    this.submitting.set(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('title', this.formData().title.trim());
      formDataToSend.append('description', this.formData().description.trim());

      // Add attachments
      this.formData().attachments.forEach((file) => {
        formDataToSend.append('attachments', file, file.name);
      });

      // Make HTTP POST request using HttpClient (with auth interceptor)
      await this.http.post<Project>('/api/v1/projects/', formDataToSend).toPromise();

      // Success
      this.closeCreateModal();
      await this.loadProjects();
      alert('¡Proyecto propuesto exitosamente! Los administradores lo revisarán pronto.');
    } catch (err: any) {
      console.error('Error creating project:', err);
      const errorMessage = err.error?.detail || err.message || 'Error al proponer el proyecto. Por favor, inténtalo nuevamente.';
      alert(errorMessage);
    } finally {
      this.submitting.set(false);
    }
  }

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

  getStatusLabel(status: string): string {
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

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('es-CL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  goBack(): void {
    this.router.navigate(['/resident-dashboard']);
  }
}
