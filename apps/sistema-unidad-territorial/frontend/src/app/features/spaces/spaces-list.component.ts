import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { SpacesService } from '../../shared/services/spaces.service';
import { SpaceDto } from '../../shared/models/spaces.models';

@Component({
  selector: 'app-spaces-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './spaces-list.component.html',
  styleUrls: ['./spaces-list.component.scss']
})
export class SpacesListComponent implements OnInit {
  private readonly spacesService = inject(SpacesService);
  private readonly router = inject(Router);

  spaces = signal<SpaceDto[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.loadSpaces();
  }

  async loadSpaces(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);

    try {
      const response = await this.spacesService.getMySpaces({ per_page: 100 }).toPromise();
      if (response) {
        this.spaces.set(response.spaces);
      }
    } catch (err: any) {
      this.error.set(err.error?.detail || 'Error al cargar los espacios');
    } finally {
      this.loading.set(false);
    }
  }

  viewSpaceDetails(spaceId: string): void {
    this.router.navigate(['/resident-dashboard/reservations/new', spaceId]);
  }
}
