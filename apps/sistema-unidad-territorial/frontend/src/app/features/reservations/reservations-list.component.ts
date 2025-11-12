import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ReservationsService } from '../../shared/services/reservations.service';
import { ReservationDto, ReservationStatus } from '../../shared/models/spaces.models';

@Component({
  selector: 'app-reservations-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reservations-list.component.html',
  styleUrls: ['./reservations-list.component.scss']
})
export class ReservationsListComponent implements OnInit {
  private readonly reservationsService = inject(ReservationsService);
  private readonly router = inject(Router);

  reservations = signal<ReservationDto[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  
  statusFilter = '';
  currentPage = 1;
  perPage = 10;
  total = signal<number>(0);

  cancelModalReservation = signal<ReservationDto | null>(null);
  cancelReason = '';
  cancelling = signal<boolean>(false);

  ngOnInit(): void {
    this.loadReservations();
  }

  async loadReservations(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);

    try {
      const filters: any = {
        page: this.currentPage,
        per_page: this.perPage
      };

      if (this.statusFilter) {
        filters.status = this.statusFilter as ReservationStatus;
      }

      const response = await this.reservationsService.getMyReservations(filters).toPromise();
      if (response) {
        this.reservations.set(response.reservations);
        this.total.set(response.total);
      }
    } catch (err: any) {
      this.error.set(err.error?.detail || 'Error al cargar las reservas');
    } finally {
      this.loading.set(false);
    }
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadReservations();
  }

  totalPages = () => Math.ceil(this.total() / this.perPage);

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

  showCancelModal(reservation: ReservationDto): void {
    this.cancelModalReservation.set(reservation);
    this.cancelReason = '';
  }

  closeCancelModal(): void {
    this.cancelModalReservation.set(null);
    this.cancelReason = '';
  }

  async confirmCancel(): Promise<void> {
    const reservation = this.cancelModalReservation();
    if (!reservation) return;

    this.cancelling.set(true);

    try {
      await this.reservationsService.cancelReservation(
        reservation.id,
        this.cancelReason || undefined
      ).toPromise();

      this.closeCancelModal();
      this.loadReservations();
    } catch (err: any) {
      this.error.set(err.error?.detail || 'Error al cancelar la reserva');
      this.closeCancelModal();
    } finally {
      this.cancelling.set(false);
    }
  }

  goToSpaces(): void {
    this.router.navigate(['/resident-dashboard/spaces']);
  }

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
}
