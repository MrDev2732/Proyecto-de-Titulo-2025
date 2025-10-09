import { Component, inject, signal, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { 
  RegistrationAdminService, 
  RegistrationRequestAdmin, 
  RegistrationRequestStatus,
  RegistrationRequestListAdmin 
} from '../../shared/services/registration-admin.service';
import { RegistrationDetailModalComponent } from './registration-detail-modal.component';

@Component({
  selector: 'app-registration-requests-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RegistrationDetailModalComponent],
  template: `
    <div class="space-y-6">

      <!-- Filtros y búsqueda -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">

          <!-- Búsqueda -->
          <div class="flex-1 max-w-md">
            <div class="relative">
              <input
                type="text"
                [(ngModel)]="searchTerm"
                (ngModelChange)="onSearchChange()"
                placeholder="Buscar por nombre, email o RUT..."
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
              </div>
            </div>
          </div>

          <!-- Filtros -->
          <div class="flex space-x-4">
            <!-- Filtro por estado -->
            <select
              [(ngModel)]="selectedStatus"
              (ngModelChange)="onFilterChange()"
              class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="ALL">Todos los estados</option>
              <option value="PENDING">Pendientes</option>
              <option value="APPROVED">Aprobadas</option>
              <option value="REJECTED">Rechazadas</option>
            </select>

            <!-- Botón refrescar -->
            <button
              (click)="loadRequests()"
              [disabled]="isLoading()"
              class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              @if (isLoading()) {
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Cargando...
              } @else {
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                Refrescar
              }
            </button>
          </div>
        </div>
      </div>

      <!-- Lista de solicitudes -->
      @if (isLoading()) {
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <div class="flex justify-center items-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span class="ml-3 text-gray-600">Cargando solicitudes...</span>
          </div>
        </div>
      } @else if (requests().length === 0) {
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
           <h3 class="mt-2 text-sm font-medium text-gray-900">No hay solicitudes</h3>
           <p class="mt-1 text-sm text-gray-500">
             @if (selectedStatus !== 'ALL' || searchTerm) {
               No se encontraron solicitudes que coincidan con los filtros.
             } @else {
               No hay solicitudes de registro disponibles para tu usuario.
             }
           </p>
        </div>
      } @else {
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">

          <!-- Header de la tabla -->
          <div class="px-6 py-3 bg-gray-50 border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-medium text-gray-900">
                Solicitudes de Registro ({{ requests().length }})
              </h3>
              @if (pendingCount() > 0) {
                <span class="inline-flex px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                  {{ pendingCount() }} pendiente{{ pendingCount() > 1 ? 's' : '' }}
                </span>
              }
            </div>
          </div>

          <!-- Tabla de solicitudes -->
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Solicitante
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Comunidad
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Documentos
                  </th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                @for (request of requests(); track request.id) {
                  <tr class="hover:bg-gray-50 transition-colors cursor-pointer" (click)="openRequestDetail(request.id)">

                    <!-- Solicitante -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="flex-shrink-0 h-10 w-10">
                          <div class="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                            <span class="text-sm font-medium text-gray-600">
                              {{ getInitials(request.full_name || request.email) }}
                            </span>
                          </div>
                        </div>
                        <div class="ml-4">
                          <div class="text-sm font-medium text-gray-900">
                            {{ request.full_name || 'Sin nombre' }}
                          </div>
                          <div class="text-sm text-gray-500">
                            {{ request.email }}
                          </div>
                          @if (request.rut) {
                            <div class="text-xs text-gray-400">
                              RUT: {{ request.rut }}
                            </div>
                          }
                        </div>
                      </div>
                    </td>

                    <!-- Comunidad -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="text-sm text-gray-900">
                        {{ request.community?.name || 'Sin comunidad' }}
                      </div>
                    </td>

                    <!-- Estado -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full"
                            [class]="registrationService.getStatusColor(request.status)">
                        {{ registrationService.getStatusLabel(request.status) }}
                      </span>
                    </td>

                    <!-- Fecha -->
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div>{{ formatShortDate(request.created_at) }}</div>
                      @if (request.decided_at) {
                        <div class="text-xs text-gray-400">
                          Decidida: {{ formatShortDate(request.decided_at) }}
                        </div>
                      }
                    </td>

                    <!-- Documentos -->
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center space-x-1">
                        <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                         <span class="text-sm text-gray-600">
                           {{ request.attachments.length || 0 }} archivo{{ (request.attachments.length || 0) !== 1 ? 's' : '' }}
                         </span>
                      </div>
                    </td>

                    <!-- Acciones -->
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div class="flex justify-end space-x-2">
                        <button
                          (click)="openRequestDetail(request.id); $event.stopPropagation()"
                          class="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-900 transition-colors rounded-md hover:bg-blue-50"
                          title="Ver detalles"
                        >
                          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                          </svg>
                          Ver
                        </button>

                        @if (request.status === RegistrationRequestStatus.PENDING) {
                          <button
                            (click)="quickApprove(request); $event.stopPropagation()"
                            class="inline-flex items-center px-2 py-1 text-xs font-medium text-green-600 hover:text-green-900 transition-colors rounded-md hover:bg-green-50"
                            title="Aprobar rápidamente"
                          >
                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                            Aprobar
                          </button>

                          <button
                            (click)="quickReject(request); $event.stopPropagation()"
                            class="inline-flex items-center px-2 py-1 text-xs font-medium text-red-600 hover:text-red-900 transition-colors rounded-md hover:bg-red-50"
                            title="Rechazar (requiere notas)"
                          >
                            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                            Rechazar
                          </button>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- Modal de detalles -->
      <app-registration-detail-modal
        [requestId]="selectedRequestId()"
        [isOpen]="detailModalOpen()"
        (closed)="closeDetailModal()"
        (requestUpdated)="onRequestUpdated($event)"
      />
    </div>
  `
})
export class RegistrationRequestsListComponent implements OnInit {
  @Input() communityId?: string;

  readonly registrationService = inject(RegistrationAdminService);

  // Estado del componente
  requests = signal<RegistrationRequestAdmin[]>([]);
  isLoading = signal(false);
  selectedRequestId = signal<string | null>(null);
  detailModalOpen = signal(false);

  // Filtros
  searchTerm = '';
  selectedStatus: RegistrationRequestStatus | 'ALL' = 'ALL';

  // Debounce para búsqueda
  private searchTimeout?: number;

  // Constantes para template
  readonly RegistrationRequestStatus = RegistrationRequestStatus;

  ngOnInit() {
    this.loadRequests();
  }

  loadRequests() {
    this.isLoading.set(true);

    const filters = {
      status: this.selectedStatus !== 'ALL' ? this.selectedStatus : undefined,
      search: this.searchTerm.trim() || undefined
    };

    // Usar el nuevo endpoint que determina automáticamente las comunidades según el usuario
    const request$ = this.communityId 
      ? this.registrationService.getRegistrationRequestsForCommunity(this.communityId)
      : this.registrationService.getAllRegistrationRequests(filters);

    request$.subscribe({
      next: (response) => {
        this.requests.set(response.requests);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Error loading requests:', error);
        this.requests.set([]);
        this.isLoading.set(false);
      }
    });
  }

  onSearchChange() {
    // Debounce búsqueda
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    this.searchTimeout = window.setTimeout(() => {
      this.loadRequests();
    }, 500);
  }

  onFilterChange() {
    this.loadRequests();
  }

  openRequestDetail(requestId: string) {
    this.selectedRequestId.set(requestId);
    this.detailModalOpen.set(true);
  }

  closeDetailModal() {
    this.detailModalOpen.set(false);
    this.selectedRequestId.set(null);
  }

  onRequestUpdated(updatedRequest: RegistrationRequestAdmin) {
    // Actualizar la solicitud en la lista
    const currentRequests = this.requests();
    const updatedRequests = currentRequests.map(req => 
      req.id === updatedRequest.id ? updatedRequest : req
    );
    this.requests.set(updatedRequests);
  }

  quickApprove(request: RegistrationRequestAdmin) {
    if (confirm(`¿Estás seguro de que quieres aprobar la solicitud de ${request.full_name || request.email}?`)) {
      this.registrationService.approveRegistrationRequest(request.id, {}).subscribe({
        next: (updatedRequest) => {
          this.onRequestUpdated(updatedRequest);
        },
        error: (error) => {
          console.error('Error approving request:', error);
          alert('Error al aprobar la solicitud. Por favor, inténtalo de nuevo.');
        }
      });
    }
  }

  quickReject(request: RegistrationRequestAdmin) {
    const notes = prompt('Ingresa las notas de rechazo (obligatorias):');
    if (notes && notes.trim().length >= 10) {
      this.registrationService.rejectRegistrationRequest(request.id, { decision_notes: notes.trim() }).subscribe({
        next: (updatedRequest) => {
          this.onRequestUpdated(updatedRequest);
        },
        error: (error) => {
          console.error('Error rejecting request:', error);
          alert('Error al rechazar la solicitud. Por favor, inténtalo de nuevo.');
        }
      });
    } else if (notes !== null) {
      alert('Las notas de rechazo son obligatorias y deben tener al menos 10 caracteres.');
    }
  }

  // Utilidades para template
  getInitials(name: string): string {
    if (!name) return '?';
    return name.split(' ')
      .map(word => word.charAt(0))
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  formatShortDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  }

  pendingCount(): number {
    return this.requests().filter(req => req.status === RegistrationRequestStatus.PENDING).length;
  }
}
