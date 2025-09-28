import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Componente reutilizable para mostrar estados de carga
 * con animaciones modernas y accesibilidad
 */
@Component({
  selector: 'app-loading-state',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex items-center justify-center py-8" [attr.aria-label]="message">
      <!-- Spinner -->
      <div 
        class="relative"
        [class]="spinnerSizeClass"
        role="status"
        aria-live="polite"
      >
        <!-- Spinner principal -->
        <div 
          class="animate-spin rounded-full border-b-2"
          [class]="'h-full w-full ' + spinnerColorClass"
        ></div>
        
        <!-- Spinner secundario para efecto de overlay -->
        <div 
          class="absolute top-0 left-0 animate-ping rounded-full border-2 opacity-20"
          [class]="'h-full w-full ' + spinnerColorClass"
        ></div>
      </div>
      
      <!-- Mensaje -->
      @if (showMessage) {
        <span 
          class="ml-3 text-sm font-medium"
          [class]="textColorClass"
        >
          {{ message }}
        </span>
      }
    </div>
  `,
  styles: [`
    .loading-dots::after {
      content: '...';
      animation: dots 1.5s steps(4, end) infinite;
    }
    
    @keyframes dots {
      0%, 20% { content: '.'; }
      40% { content: '..'; }
      60% { content: '...'; }
      80%, 100% { content: ''; }
    }
  `]
})
export class LoadingStateComponent {
  @Input() message: string = 'Cargando...';
  @Input() size: 'small' | 'medium' | 'large' = 'medium';
  @Input() color: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' = 'primary';
  @Input() showMessage: boolean = true;

  get spinnerSizeClass(): string {
    switch (this.size) {
      case 'small':
        return 'h-4 w-4';
      case 'large':
        return 'h-12 w-12';
      case 'medium':
      default:
        return 'h-8 w-8';
    }
  }

  get spinnerColorClass(): string {
    switch (this.color) {
      case 'secondary':
        return 'border-gray-600';
      case 'success':
        return 'border-green-600';
      case 'warning':
        return 'border-yellow-600';
      case 'danger':
        return 'border-red-600';
      case 'primary':
      default:
        return 'border-blue-600';
    }
  }

  get textColorClass(): string {
    switch (this.color) {
      case 'secondary':
        return 'text-gray-600';
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'danger':
        return 'text-red-600';
      case 'primary':
      default:
        return 'text-blue-600';
    }
  }
}
