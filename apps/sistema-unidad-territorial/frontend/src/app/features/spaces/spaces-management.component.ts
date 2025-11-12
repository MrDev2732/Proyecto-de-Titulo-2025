import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SpacesService } from '../../shared/services/spaces.service';
import { SpaceDto, SpaceCreateDto, SpaceUpdateDto } from '../../shared/models/spaces.models';

@Component({
  selector: 'app-spaces-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './spaces-management.component.html',
  styleUrls: ['./spaces-management.component.scss']
})
export class SpacesManagementComponent implements OnInit {
  private readonly spacesService = inject(SpacesService);

  // Estado del componente
  spaces = signal<SpaceDto[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // Modales
  showCreateModal = signal<boolean>(false);
  showEditModal = signal<boolean>(false);
  showDeleteModal = signal<boolean>(false);
  
  // Espacio en edición/eliminación
  selectedSpace = signal<SpaceDto | null>(null);
  processing = signal<boolean>(false);

  // Formulario
  spaceForm = {
    name: '',
    description: '',
    capacity: null as number | null,
    requires_approval: true,
    rules_json: {
      max_hours_daily: null as number | null,
      max_hours_weekly: null as number | null,
      min_duration_hours: null as number | null,
      max_duration_hours: null as number | null,
      advance_days_required: null as number | null
    }
  };

  ngOnInit(): void {
    this.loadSpaces();
  }

  /**
   * Cargar todos los espacios de la comunidad
   */
  async loadSpaces(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.successMessage.set(null);

    try {
      const response = await this.spacesService.getMySpaces({ per_page: 100 }).toPromise();
      if (response) {
        this.spaces.set(response.spaces);
      }
    } catch (err: any) {
      console.error('Error loading spaces:', err);

      if (err.status === 403) {
        this.error.set('⛔ No tienes permisos administrativos. Se requiere rol de ADMIN, MODERATOR o SUPERADMIN.');
      } else if (err.status === 401) {
        this.error.set('❌ No estás autenticado. Por favor, inicia sesión nuevamente.');
      } else {
        this.error.set(err.error?.detail || 'Error al cargar los espacios');
      }
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Abrir modal de creación
   */
  openCreateModal(): void {
    this.resetForm();
    this.showCreateModal.set(true);
  }

  /**
   * Abrir modal de edición
   */
  openEditModal(space: SpaceDto): void {
    this.selectedSpace.set(space);
    this.spaceForm = {
      name: space.name,
      description: space.description || '',
      capacity: space.capacity || null,
      requires_approval: space.requires_approval,
      rules_json: {
        max_hours_daily: space.rules_json?.max_hours_daily || null,
        max_hours_weekly: space.rules_json?.max_hours_weekly || null,
        min_duration_hours: space.rules_json?.min_duration_hours || null,
        max_duration_hours: space.rules_json?.max_duration_hours || null,
        advance_days_required: space.rules_json?.advance_days_required || null
      }
    };
    this.showEditModal.set(true);
  }

  /**
   * Abrir modal de eliminación
   */
  openDeleteModal(space: SpaceDto): void {
    this.selectedSpace.set(space);
    this.showDeleteModal.set(true);
  }

  /**
   * Cerrar todos los modales
   */
  closeModals(): void {
    this.showCreateModal.set(false);
    this.showEditModal.set(false);
    this.showDeleteModal.set(false);
    this.selectedSpace.set(null);
    this.resetForm();
  }

  /**
   * Resetear formulario
   */
  resetForm(): void {
    this.spaceForm = {
      name: '',
      description: '',
      capacity: null,
      requires_approval: true,
      rules_json: {
        max_hours_daily: null,
        max_hours_weekly: null,
        min_duration_hours: null,
        max_duration_hours: null,
        advance_days_required: null
      }
    };
  }

  /**
   * Crear nuevo espacio
   */
  async createSpace(): Promise<void> {
    if (!this.validateForm()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      const spaceData: SpaceCreateDto = {
        name: this.spaceForm.name,
        description: this.spaceForm.description || undefined,
        capacity: this.spaceForm.capacity || undefined,
        requires_approval: this.spaceForm.requires_approval,
        rules_json: this.cleanRulesJson(this.spaceForm.rules_json)
      };

      await this.spacesService.createSpace(spaceData).toPromise();
      this.successMessage.set('✅ Espacio creado exitosamente');
      this.closeModals();
      this.loadSpaces();

      // Limpiar mensaje después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error creating space:', err);

      if (err.status === 403) {
        this.error.set('⛔ No tienes permisos administrativos. Se requiere rol de ADMIN, MODERATOR o SUPERADMIN.');
      } else if (err.status === 401) {
        this.error.set('❌ No estás autenticado. Por favor, inicia sesión nuevamente.');
      } else {
        this.error.set(err.error?.detail || 'Error al crear el espacio');
      }
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Actualizar espacio existente
   */
  async updateSpace(): Promise<void> {
    const space = this.selectedSpace();
    if (!space || !this.validateForm()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      const spaceData: SpaceUpdateDto = {
        name: this.spaceForm.name,
        description: this.spaceForm.description || undefined,
        capacity: this.spaceForm.capacity || undefined,
        requires_approval: this.spaceForm.requires_approval,
        rules_json: this.cleanRulesJson(this.spaceForm.rules_json)
      };

      await this.spacesService.updateSpace(space.id, spaceData).toPromise();
      this.successMessage.set('✅ Espacio actualizado exitosamente');
      this.closeModals();
      this.loadSpaces();

      // Limpiar mensaje después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error updating space:', err);
      this.error.set(err.error?.detail || 'Error al actualizar el espacio');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Eliminar espacio
   */
  async deleteSpace(): Promise<void> {
    const space = this.selectedSpace();
    if (!space) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.spacesService.deleteSpace(space.id).toPromise();
      this.successMessage.set('✅ Espacio eliminado exitosamente');
      this.closeModals();
      this.loadSpaces();

      // Limpiar mensaje después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error deleting space:', err);
      this.error.set(err.error?.detail || 'Error al eliminar el espacio');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Validar formulario
   */
  validateForm(): boolean {
    if (!this.spaceForm.name || this.spaceForm.name.trim().length < 3) {
      this.error.set('El nombre debe tener al menos 3 caracteres');
      return false;
    }

    if (this.spaceForm.capacity !== null && this.spaceForm.capacity < 1) {
      this.error.set('La capacidad debe ser mayor a 0');
      return false;
    }

    return true;
  }

  /**
   * Limpiar rules_json eliminando valores nulos
   */
  cleanRulesJson(rules: any): any {
    const cleanRules: any = {};

    if (rules.max_hours_daily !== null && rules.max_hours_daily > 0) {
      cleanRules.max_hours_daily = rules.max_hours_daily;
    }
    if (rules.max_hours_weekly !== null && rules.max_hours_weekly > 0) {
      cleanRules.max_hours_weekly = rules.max_hours_weekly;
    }
    if (rules.min_duration_hours !== null && rules.min_duration_hours > 0) {
      cleanRules.min_duration_hours = rules.min_duration_hours;
    }
    if (rules.max_duration_hours !== null && rules.max_duration_hours > 0) {
      cleanRules.max_duration_hours = rules.max_duration_hours;
    }
    if (rules.advance_days_required !== null && rules.advance_days_required > 0) {
      cleanRules.advance_days_required = rules.advance_days_required;
    }

    return Object.keys(cleanRules).length > 0 ? cleanRules : undefined;
  }

  /**
   * Formatear fecha
   */
  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-CL', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  }
}
