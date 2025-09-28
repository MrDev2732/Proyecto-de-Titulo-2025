import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Componente de animación de bienvenida
 * Se muestra después del login antes de cargar el dashboard
 */
@Component({
  selector: 'app-welcome-animation',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      class="fixed inset-0 bg-gradient-to-br from-green-50 to-green-100 flex items-center justify-center z-50 transition-opacity duration-1000"
      [class.opacity-0]="isHiding"
      [class.opacity-100]="!isHiding"
    >
      <div class="text-center max-w-md mx-auto px-6">
        <!-- Logo animado -->
        <div class="mb-8 animate-bounce-gentle">
          <div class="w-32 h-32 mx-auto bg-white rounded-2xl flex items-center justify-center shadow-2xl border border-gray-200">
            <img
              src="assets/images/municipal-logo.png"
              alt="Logo Municipal"
              class="w-24 h-24 object-contain"
              (error)="onImageError($event)"
            >
            <!-- SVG fallback (oculto por defecto) -->
            <svg class="w-16 h-16 text-green-500 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
            </svg>
          </div>
        </div>

        <!-- Mensaje de bienvenida -->
        <div class="animate-fade-in-up">
          <h1 class="text-3xl font-bold text-gray-800 mb-4">
            ¡Bienvenido{{ userName ? ', ' + userName : '' }}!
          </h1>
          <p class="text-lg text-gray-600 mb-6">
            Sistema de Gestión de Unidades Territoriales
          </p>
          <p class="text-sm text-gray-500">
            Cargando panel de administración...
          </p>
        </div>

        <!-- Indicador de progreso -->
        <div class="mt-8">
          <div class="w-48 h-1 bg-gray-200 rounded-full mx-auto overflow-hidden">
            <div class="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full animate-progress"></div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    @keyframes bounce-gentle {
      0%, 100% { 
        transform: translateY(0); 
      }
      50% { 
        transform: translateY(-10px); 
      }
    }

    @keyframes fade-in-up {
      0% {
        opacity: 0;
        transform: translateY(30px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes progress {
      0% {
        width: 0%;
      }
      100% {
        width: 100%;
      }
    }

    .animate-bounce-gentle {
      animation: bounce-gentle 2s ease-in-out infinite;
    }

    .animate-fade-in-up {
      animation: fade-in-up 0.8s ease-out 0.3s both;
    }

    .animate-progress {
      animation: progress 2.5s ease-in-out;
    }
  `]
})
export class WelcomeAnimationComponent implements OnInit {
  @Input() userName?: string;
  @Output() animationComplete = new EventEmitter<void>();

  isHiding = false;

  ngOnInit() {
    // Mostrar la animación por 3 segundos, luego empezar a ocultar
    setTimeout(() => {
      this.isHiding = true;
      // Esperar a que termine la transición de opacity antes de emitir el evento
      setTimeout(() => {
        this.animationComplete.emit();
      }, 1000);
    }, 3000);
  }

  onImageError(event: Event): void {
    // Ocultar la imagen que falló y mostrar el SVG fallback
    const imgElement = event.target as HTMLImageElement;
    const parentElement = imgElement.parentElement;

    if (parentElement) {
      // Ocultar la imagen
      imgElement.style.display = 'none';

      // Mostrar el SVG fallback
      const fallbackSvg = parentElement.querySelector('svg');
      if (fallbackSvg) {
        fallbackSvg.classList.remove('hidden');
      }
    }
  }
}
