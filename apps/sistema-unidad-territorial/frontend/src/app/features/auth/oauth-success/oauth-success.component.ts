import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../../shared/auth/auth.service';
import { getDashboardRoute } from '../../../shared/auth/role.utils';

@Component({
	selector: 'app-oauth-success',
	standalone: true,
	imports: [CommonModule],
	template: `
		<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-municipal-bg via-white to-municipal-light/20">
			<div class="text-center">
				<div class="w-16 h-16 mx-auto mb-4 bg-municipal-green rounded-full flex items-center justify-center animate-pulse">
					<svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
						<path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
					</svg>
				</div>
				<h2 class="text-2xl font-semibold text-municipal-dark mb-2">¡Autenticación Exitosa!</h2>
				<p class="text-municipal-muted">Redirigiendo al dashboard...</p>

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
		.animate-pulse {
			animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
		}

		@keyframes pulse {
			0%, 100% { opacity: 1; }
			50% { opacity: .5; }
		}
	`]
})
export class OAuthSuccessComponent implements OnInit {
	private readonly router = inject(Router);
	private readonly route = inject(ActivatedRoute);
	private readonly auth = inject(AuthService);

	error: string | null = null;

	async ngOnInit(): Promise<void> {
		try {
			// Obtener tokens de los parámetros de URL (si el backend los envía)
			const accessToken = this.route.snapshot.queryParams['access_token'];
			const refreshToken = this.route.snapshot.queryParams['refresh_token'];
			const userJson = this.route.snapshot.queryParams['user'];

			if (accessToken && refreshToken && userJson) {
				// El backend envió los tokens en la URL
				this.persistTokensFromUrl(accessToken, refreshToken, userJson);

				// Marcar como autenticado
				this.auth.isAuthenticated.set(true);

				try {
					const user = JSON.parse(decodeURIComponent(userJson));
					this.auth.currentUser.set(user);
				} catch {
					// Si no se puede parsear el usuario, continuar sin él
					this.auth.currentUser.set(null);
				}

				// Redirigir al dashboard apropiado según el rol
				setTimeout(() => {
					const user = this.auth.currentUser();
					const dashboardRoute = getDashboardRoute(user);
					this.router.navigateByUrl(dashboardRoute);
				}, 1500);
			} else {
				// No hay tokens en la URL, verificar si ya está autenticado
				if (this.auth.isAuthenticated()) {
					const user = this.auth.currentUser();
					const dashboardRoute = getDashboardRoute(user);
					this.router.navigateByUrl(dashboardRoute);
				} else {
					this.error = 'No se recibieron los datos de autenticación';
				}
			}

		} catch (err: any) {
			console.error('Error en OAuth success:', err);
			this.error = 'Error al procesar la autenticación';
		}
	}

	private persistTokensFromUrl(accessToken: string, refreshToken: string, userJson: string): void {
		// Usar localStorage para persistir los tokens
		localStorage.setItem('sut.access', accessToken);
		localStorage.setItem('sut.refresh', refreshToken);
		localStorage.setItem('sut.user', decodeURIComponent(userJson));

		// Limpiar sessionStorage
		sessionStorage.removeItem('sut.access');
		sessionStorage.removeItem('sut.refresh');
		sessionStorage.removeItem('sut.user');
	}

	redirectToSignin(): void {
		this.router.navigateByUrl('/signin');
	}
}
