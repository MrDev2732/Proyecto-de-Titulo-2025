import { Routes } from '@angular/router';

export const AUTH_ROUTES: Routes = [
	{
		path: 'signin',
		loadComponent: () => import('./signin/signin.component').then(m => m.SigninComponent),
		data: { title: 'Acceso Administrativo' }
	},
	// Redirigir login genérico al login de admin
	{
		path: 'signin',
		redirectTo: 'signin'
	},
];	
