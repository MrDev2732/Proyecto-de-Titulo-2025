import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../../shared/auth/auth.service';
import { TokenResponseDto } from '../../../shared/auth/auth.models';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Component({
	selector: 'app-google-callback',
	standalone: true,
	imports: [CommonModule],
	template: `
		<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-municipal-bg via-white to-municipal-light/20">
			<div class="text-center">
				<div class="w-16 h-16 mx-auto mb-4 bg-municipal-green rounded-full flex items-center justify-center animate-pulse">
					<svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
						<path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
					</svg>
				</div>
				<h2 class="text-2xl font-semibold text-municipal-dark mb-2">Procesando Autenticación</h2>
				<p class="text-municipal-muted">Completando el acceso con Google Workspace...</p>
				
				<div *ngIf="error" class="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
					<p class="text-red-800 text-sm">{{ error }}</p>
					<button 
						(click)="redirectToSignin()"
						class="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
					>
						Volver al Login
					</button>
				</div>
			</div>
		</div>
	`,
	styles: [`
		.animate-spin {
			animation: spin 1s linear infinite;
		}
		
		@keyframes spin {
			from { transform: rotate(0deg); }
			to { transform: rotate(360deg); }
		}
	`]
})
export class GoogleCallbackComponent implements OnInit {
	private readonly router = inject(Router);
	private readonly route = inject(ActivatedRoute);
	private readonly auth = inject(AuthService);
	private readonly http = inject(HttpClient);

	error: string | null = null;

	async ngOnInit(): Promise<void> {
		try {
			// Obtener parámetros de la URL
			const code = this.route.snapshot.queryParams['code'];
			const state = this.route.snapshot.queryParams['state'];
			const error = this.route.snapshot.queryParams['error'];

			console.log('🔍 OAuth Callback - Parámetros recibidos:', { 
				hasCode: !!code, 
				hasState: !!state, 
				error 
			});

			if (error) {
				console.error('❌ OAuth Error recibido de Google:', error);
				this.error = 'Error en la autenticación con Google: ' + error;
				return;
			}

			if (!code) {
				console.error('❌ No se recibió código de autorización');
				this.error = 'Código de autorización no recibido';
				return;
			}

			// Enviar el código al backend para completar la autenticación
			console.log('🔄 Enviando código al backend...');
			const response = await firstValueFrom(
				this.http.get<TokenResponseDto>('/api/v1/auth/google/callback', {
					params: {
						code,
						state
					}
				})
			);

			console.log('✅ Respuesta exitosa del backend:', { 
				hasAccessToken: !!response.access_token,
				hasRefreshToken: !!response.refresh_token,
				userEmail: response.user?.email 
			});

			// Persistir los tokens usando el AuthService
			this.persistGoogleTokens(response);

			// Marcar como autenticado
			this.auth.isAuthenticated.set(true);
			this.auth.currentUser.set(response.user);

			console.log('🎯 Redirigiendo al dashboard...');
			// Redirigir al dashboard administrativo
			await this.router.navigateByUrl('/admin-dashboard');

		} catch (err: any) {
			console.error('❌ Error en callback de Google:', err);
			console.error('❌ Detalles del error:', {
				status: err.status,
				statusText: err.statusText,
				error: err.error,
				message: err.message
			});

			// Determinar el mensaje de error apropiado
			let errorMessage = 'Error al procesar la autenticación con Google';

			if (err.status === 403) {
				errorMessage = 'Su cuenta no está aprobada para acceder al sistema. Contacte a los moderadores de su comunidad.';
			} else if (err.status === 400) {
				errorMessage = err.error?.detail || 'Código de autorización inválido o expirado';
			} else if (err.status === 422) {
				errorMessage = 'Parámetros de callback inválidos';
			} else if (err.error?.detail) {
				errorMessage = err.error.detail;
			}

			this.error = errorMessage;

			// NO redirigir al dashboard en caso de error
			// El usuario verá el mensaje de error y podrá usar el botón "Volver al Login"
			return;
		}
	}

	private persistGoogleTokens(response: TokenResponseDto): void {
		// Usar localStorage por defecto para Google OAuth (considerarlo como "recordar sesión")
		localStorage.setItem('sut.access', response.access_token);
		localStorage.setItem('sut.refresh', response.refresh_token);
		localStorage.setItem('sut.user', JSON.stringify(response.user));

		// Limpiar sessionStorage por si acaso
		sessionStorage.removeItem('sut.access');
		sessionStorage.removeItem('sut.refresh');
		sessionStorage.removeItem('sut.user');
	}

	redirectToSignin(): void {
		this.router.navigateByUrl('/signin');
	}
}
