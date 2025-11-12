import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ReservationsService } from '../../shared/services/reservations.service';
import { SpacesService } from '../../shared/services/spaces.service';
import { SpaceDto, ReservationDto } from '../../shared/models/spaces.models';

@Component({
  selector: 'app-reservations-create',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './reservations-create.component.html',
  styleUrls: ['./reservations-create.component.scss']
})
export class ReservationsCreateComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly reservationsService = inject(ReservationsService);
  private readonly spacesService = inject(SpacesService);

  space = signal<SpaceDto | null>(null);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  selectedDate = '';
  startTime = '';
  endTime = '';

  isAvailable = signal<boolean>(false);
  availabilityChecked = signal<boolean>(false);
  availabilityMessage = signal<string>('');
  checkingAvailability = signal<boolean>(false);

  upcomingReservations = signal<ReservationDto[]>([]);
  successMessage = signal<string | null>(null);

  minDate = new Date().toISOString().split('T')[0];

  ngOnInit(): void {
    const spaceId = this.route.snapshot.paramMap.get('id');
    if (spaceId) {
      this.loadSpace(spaceId);
      this.loadUpcomingReservations(spaceId);
    } else {
      this.error.set('ID de espacio no válido');
    }
  }

  async loadSpace(id: string): Promise<void> {
    this.loading.set(true);
    try {
      const space = await this.spacesService.getSpace(id).toPromise();
      if (space) {
        this.space.set(space);
      }
    } catch (err: any) {
      this.error.set(err.error?.detail || 'Error al cargar el espacio');
    } finally {
      this.loading.set(false);
    }
  }

  async loadUpcomingReservations(spaceId: string): Promise<void> {
    try {
      const startDate = new Date().toISOString();
      const endDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
      const response = await this.reservationsService.getSpaceCalendar(spaceId, startDate, endDate).toPromise();
      if (response) {
        this.upcomingReservations.set(response.reservations.filter(r => r.status !== 'CANCELLED').slice(0, 5));
      }
    } catch (err) {
      // Silently fail
    }
  }

  onDateChange(): void {
    if (this.selectedDate && this.startTime && this.endTime) {
      this.checkAvailability();
    }
  }

  async checkAvailability(): Promise<void> {
    if (!this.selectedDate || !this.startTime || !this.endTime || !this.space()) {
      return;
    }

    this.checkingAvailability.set(true);
    this.availabilityChecked.set(false);

    try {
      const startDateTime = `${this.selectedDate}T${this.startTime}:00`;
      const endDateTime = `${this.selectedDate}T${this.endTime}:00`;

      const response = await this.reservationsService.checkAvailability({
        space_id: this.space()!.id,
        start_time: startDateTime,
        end_time: endDateTime
      }).toPromise();

      if (response) {
        this.isAvailable.set(response.is_available);
        this.availabilityMessage.set(response.message);
        this.availabilityChecked.set(true);
      }
    } catch (err: any) {
      this.isAvailable.set(false);
      this.availabilityMessage.set(err.error?.detail || 'Error al verificar disponibilidad');
      this.availabilityChecked.set(true);
    } finally {
      this.checkingAvailability.set(false);
    }
  }

  canSubmit(): boolean {
    return this.availabilityChecked() && this.isAvailable() && !this.checkingAvailability();
  }

  async createReservation(): Promise<void> {
    if (!this.canSubmit() || !this.space()) {
      return;
    }

    try {
      const startDateTime = `${this.selectedDate}T${this.startTime}:00`;
      const endDateTime = `${this.selectedDate}T${this.endTime}:00`;

      const reservation = await this.reservationsService.createReservation({
        space_id: this.space()!.id,
        start_time: startDateTime,
        end_time: endDateTime
      }).toPromise();

      if (reservation) {
        if (this.space()!.requires_approval) {
          this.successMessage.set('Tu solicitud de reserva ha sido enviada y está pendiente de aprobación.');
        } else {
          this.successMessage.set('Tu reserva ha sido confirmada exitosamente.');
        }
      }
    } catch (err: any) {
      this.error.set(err.error?.detail || 'Error al crear la reserva');
    }
  }

  goBack(): void {
    this.router.navigate(['/resident-dashboard/spaces']);
  }

  goToMyReservations(): void {
    this.router.navigate(['/resident-dashboard/reservations']);
  }

  closeSuccessModal(): void {
    this.successMessage.set(null);
    this.selectedDate = '';
    this.startTime = '';
    this.endTime = '';
    this.availabilityChecked.set(false);
    if (this.space()) {
      this.loadUpcomingReservations(this.space()!.id);
    }
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-CL', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
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
