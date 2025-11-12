import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ReservationsService } from '../../shared/services/reservations.service';
import { ReservationDto, ReservationStatus } from '../../shared/models/spaces.models';

@Component({
  selector: 'app-community-reservations-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './community-reservations-list.component.html',
  styleUrls: ['./community-reservations-list.component.scss']
})
export class CommunityReservationsListComponent implements OnInit {
  private readonly reservationsService = inject(ReservationsService);
  private readonly router = inject(Router);

  // Estado del componente
  reservations = signal<ReservationDto[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // Filtros
  statusFilter = '';
  spaceFilter = '';
  currentPage = 1;
  perPage = 20;
  total = signal<number>(0);
  totalPages = signal<number>(1);

  // Modales
  approvalModalReservation = signal<ReservationDto | null>(null);
  rejectReason = '';
  processing = signal<boolean>(false);

  // Computed
  pendingCount = computed(() => 
    this.reservations().filter(r => r.status === ReservationStatus.PENDING).length
  );

  confirmedCount = computed(() => 
    this.reservations().filter(r => r.status === ReservationStatus.CONFIRMED).length
  );

  cancelledCount = computed(() => 
    this.reservations().filter(r => r.status === ReservationStatus.CANCELLED).length
  );

  ngOnInit(): void {
    this.loadReservations();
  }

  /**
   * Cargar todas las reservas de la comunidad
   */
  async loadReservations(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.successMessage.set(null);

    try {
      const filters: any = {
        page: this.currentPage,
        per_page: this.perPage
      };

      if (this.statusFilter) {
        filters.status = this.statusFilter;
      }

      if (this.spaceFilter) {
        filters.space_id = this.spaceFilter;
      }

      const response = await this.reservationsService.getCommunityReservations(filters).toPromise();

      if (response) {
        this.reservations.set(response.reservations);
        this.total.set(response.total);
        this.totalPages.set(response.total_pages || Math.ceil(response.total / this.perPage));
      }
    } catch (err: any) {
      console.error('Error loading reservations:', err);
      this.error.set(err.error?.detail || 'Error al cargar las reservas de la comunidad');
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Manejar cambio de filtros
   */
  onFilterChange(): void {
    this.currentPage = 1;
    this.loadReservations();
  }

  /**
   * Navegación de páginas
   */
  nextPage(): void {
    if (this.currentPage < this.totalPages()) {
      this.currentPage++;
      this.loadReservations();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadReservations();
    }
  }

  /**
   * Mostrar modal de aprobación
   */
  showApprovalModal(reservation: ReservationDto): void {
    this.approvalModalReservation.set(reservation);
    this.rejectReason = '';
  }

  /**
   * Cerrar modal
   */
  closeApprovalModal(): void {
    this.approvalModalReservation.set(null);
    this.rejectReason = '';
  }

  /**
   * Aprobar una reserva
   */
  async approveReservation(reservation: ReservationDto): Promise<void> {
    if (!confirm('¿Confirmar aprobación de esta reserva?')) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.reservationsService.approveReservation(reservation.id, {
        status: 'CONFIRMED'
      }).toPromise();

      this.successMessage.set('✅ Reserva aprobada exitosamente');
      this.loadReservations();

      // Limpiar mensaje después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error approving reservation:', err);
      this.error.set(err.error?.detail || 'Error al aprobar la reserva');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Rechazar una reserva (con modal)
   */
  async confirmReject(): Promise<void> {
    const reservation = this.approvalModalReservation();
    if (!reservation) return;

    if (!this.rejectReason || this.rejectReason.trim().length < 10) {
      this.error.set('Por favor, proporciona un motivo de rechazo (mínimo 10 caracteres)');
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.reservationsService.approveReservation(reservation.id, {
        status: 'CANCELLED',
        cancel_reason: this.rejectReason
      }).toPromise();

      this.successMessage.set('✅ Reserva rechazada exitosamente');
      this.closeApprovalModal();
      this.loadReservations();

      // Limpiar mensaje después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error rejecting reservation:', err);
      this.error.set(err.error?.detail || 'Error al rechazar la reserva');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Formateo de fechas y tiempos
   */
  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-CL', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
  }

  formatDateTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleString('es-CL', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getDuration(start: string, end: string): string {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const durationMs = endDate.getTime() - startDate.getTime();
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));

    if (minutes === 0) {
      return `${hours} hora${hours !== 1 ? 's' : ''}`;
    }
    return `${hours}h ${minutes}m`;
  }

  isPast(dateStr: string): boolean {
    return new Date(dateStr) < new Date();
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'PENDING': 'Pendiente',
      'CONFIRMED': 'Confirmada',
      'CANCELLED': 'Cancelada'
    };
    return labels[status] || status;
  }

  getStatusIcon(status: string): string {
    const icons: Record<string, string> = {
      'PENDING': '⏳',
      'CONFIRMED': '✅',
      'CANCELLED': '❌'
    };
    return icons[status] || '📋';
  }

  /**
   * Verificar si la reserva puede ser aprobada/rechazada
   */
  canManageReservation(reservation: ReservationDto): boolean {
    return reservation.status === ReservationStatus.PENDING && !this.isPast(reservation.start_time);
  }
}
