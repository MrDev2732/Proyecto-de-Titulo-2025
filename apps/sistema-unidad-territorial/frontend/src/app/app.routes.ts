import { Route } from '@angular/router';
import { authGuard } from './shared/auth/auth.guard';
import { oauthDashboardGuard } from './shared/auth/oauth-dashboard.guard';
import { LoginComponent } from './features/auth/login/login.component';
import { GoogleCallbackComponent } from './features/auth/google-callback/google-callback.component';
import { OAuthSuccessComponent } from './features/auth/oauth-success/oauth-success.component';
import { DashboardComponent } from './features/shell/dashboard.component';

export const appRoutes: Route[] = [
	// Redirigir raíz al login administrativo
	{ path: '', redirectTo: '/auth/admin-login', pathMatch: 'full' },
	
	// Rutas de autenticación para administradores
	{
		path: 'auth',
		children: [
			{ 
				path: 'admin-login', 
				component: LoginComponent,
				data: { title: 'Panel de Administración Municipal' }
			},
			// Mantener compatibilidad con login genérico
			{ path: 'login', redirectTo: 'admin-login' },
			// Callback de Google OAuth (para configuración GCP futura)
			{
				path: 'google/callback',
				component: GoogleCallbackComponent,
				data: { title: 'Procesando Autenticación Google' }
			},
			// OAuth Success (para solución temporal con backend redirect)
			{
				path: 'oauth-success',
				component: OAuthSuccessComponent,
				data: { title: 'Autenticación Exitosa' }
			},
		],
	},

	// Dashboard administrativo protegido (con manejo OAuth)
	{ 
		path: 'admin-dashboard', 
		canActivate: [oauthDashboardGuard], 
		component: DashboardComponent,
		data: { title: 'Dashboard Administrativo' }
	},

	// Compatibilidad con dashboard genérico
	{ path: 'dashboard', redirectTo: '/admin-dashboard' },

	// Redirigir rutas no encontradas al login administrativo
	{ path: '**', redirectTo: '/auth/admin-login' },
];
