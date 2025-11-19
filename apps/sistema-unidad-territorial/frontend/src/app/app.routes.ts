import { Route } from '@angular/router';
import { oauthDashboardGuard } from './shared/auth/oauth-dashboard.guard';
import { authGuard } from './shared/auth/auth.guard';
import { SigninComponent } from './features/auth/signin/signin.component';
import { GoogleCallbackComponent } from './features/auth/google-callback/google-callback.component';
import { OAuthSuccessComponent } from './features/auth/oauth-success/oauth-success.component';
import { DashboardComponent } from './features/shell/dashboard.component';
import { SignupComponent } from './features/auth/signup/signup.component';
import { ResidentDashboardComponent } from './features/resident/resident-dashboard.component';


export const appRoutes: Route[] = [
	// Ruta pública de registro para vecinos
	{ 
		path: 'signup', 
		component: SignupComponent,
		data: { title: 'Registro de Vecino' }
	},

	// Redirigir raíz al login administrativo
	{ path: '', redirectTo: '/signin', pathMatch: 'full' },
	
	// Rutas de autenticación para administradores
	{
		path: '',
		children: [
			{ 
				path: 'signin', 
				component: SigninComponent,
				data: { title: 'Panel de Administración Municipal' }
			},
			// Mantener compatibilidad con login genérico
			{ path: 'signin', redirectTo: 'signin' },
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

	// Dashboard de residentes protegido
	{ 
		path: 'resident-dashboard', 
		canActivate: [authGuard], 
		component: ResidentDashboardComponent,
		data: { title: 'Portal del Residente' },
		children: [
			{
				path: 'spaces',
				loadComponent: () => import('./features/spaces/spaces-list.component').then(m => m.SpacesListComponent),
				data: { title: 'Espacios Disponibles' }
			},
			{
				path: 'reservations',
				loadComponent: () => import('./features/reservations/reservations-list.component').then(m => m.ReservationsListComponent),
				data: { title: 'Mis Reservas' }
			},
			{
				path: 'reservations/new/:id',
				loadComponent: () => import('./features/reservations/reservations-create.component').then(m => m.ReservationsCreateComponent),
				data: { title: 'Nueva Reserva' }
			},
			{
				path: 'projects',
				loadComponent: () => import('./features/resident/user-projects.component').then(m => m.UserProjectsComponent),
				data: { title: 'Mis Proyectos' }
			}
		]
	},

	// Compatibilidad con dashboard genérico
	{ path: 'dashboard', redirectTo: '/admin-dashboard' },

	// Redirigir rutas no encontradas al login administrativo
	{ path: '**', redirectTo: '/signin' },
];
