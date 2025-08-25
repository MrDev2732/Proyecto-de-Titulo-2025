import { Routes } from '@angular/router';

export const AUTH_ROUTES: Routes = [
	{
		path: 'admin-login',
		loadComponent: () => import('./login/login.component').then(m => m.LoginComponent),
		data: { title: 'Acceso Administrativo' }
	},
	// Redirigir login genérico al login de admin
	{
		path: 'login',
		redirectTo: 'admin-login'
	},
];
