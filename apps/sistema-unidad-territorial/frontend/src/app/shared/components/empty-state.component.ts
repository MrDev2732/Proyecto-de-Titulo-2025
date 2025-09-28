import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Componente reutilizable para mostrar estados vacíos
 * con iconos y mensajes personalizables
 */
@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="text-center py-12">
      <!-- Icono -->
      <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-gray-100 mb-4">
        @switch (iconType) {
          @case ('document') {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
          }
          @case ('users') {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
            </svg>
          }
          @case ('search') {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
          }
          @case ('inbox') {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
            </svg>
          }
          @case ('folder') {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
            </svg>
          }
          @default {
            <svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
            </svg>
          }
        }
      </div>
      
      <!-- Título -->
      <h3 class="text-lg font-medium text-gray-900 mb-2">{{ title }}</h3>
      
      <!-- Descripción -->
      <p class="text-sm text-gray-500 max-w-md mx-auto mb-6">{{ description }}</p>
      
      <!-- Botón de acción opcional -->
      @if (actionText && actionCallback) {
        <button
          type="button"
          (click)="onActionClick()"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          @if (actionIcon) {
            <svg class="mr-2 -ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" [attr.d]="actionIcon"></path>
            </svg>
          }
          {{ actionText }}
        </button>
      }
      
      <!-- Contenido adicional proyectado -->
      <div class="mt-6">
        <ng-content></ng-content>
      </div>
    </div>
  `
})
export class EmptyStateComponent {
  @Input() title: string = 'No hay elementos';
  @Input() description: string = 'No se encontraron elementos para mostrar.';
  @Input() iconType: 'document' | 'users' | 'search' | 'inbox' | 'folder' | 'default' = 'default';
  @Input() actionText?: string;
  @Input() actionIcon?: string; // SVG path para el icono del botón
  @Input() actionCallback?: () => void;

  onActionClick(): void {
    if (this.actionCallback) {
      this.actionCallback();
    }
  }
}
