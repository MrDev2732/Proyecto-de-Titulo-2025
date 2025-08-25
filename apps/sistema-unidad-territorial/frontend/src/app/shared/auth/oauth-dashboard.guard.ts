import { inject } from '@angular/core';
import { Router, ActivatedRouteSnapshot } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Helper functions para manejar cookies
 */
function getCookie(name: string): string | null {
	const nameEQ = name + "=";
	const ca = document.cookie.split(';');
	for (let i = 0; i < ca.length; i++) {
		let c = ca[i];
		while (c.charAt(0) === ' ') c = c.substring(1, c.length);
		if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
	}
	return null;
}

function deleteCookie(name: string): void {
	document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}

/**
 * Guard especial para el dashboard que maneja tokens OAuth en la URL
 */
export const oauthDashboardGuard = (route: ActivatedRouteSnapshot) => {
	const auth = inject(AuthService);
	const router = inject(Router);

	// Verificar si hay tokens OAuth en cookies (más seguro que URL params)
	const accessToken = getCookie('oauth_access_token');
	const refreshToken = getCookie('oauth_refresh_token');
	const userJson = getCookie('oauth_user');

	if (accessToken && refreshToken && userJson) {
		try {
			// Persistir tokens del OAuth
			localStorage.setItem('sut.access', accessToken);
			localStorage.setItem('sut.refresh', refreshToken);
			localStorage.setItem('sut.user', userJson);

			// Limpiar sessionStorage
			sessionStorage.removeItem('sut.access');
			sessionStorage.removeItem('sut.refresh');
			sessionStorage.removeItem('sut.user');

			// Limpiar cookies OAuth (ya no las necesitamos)
			deleteCookie('oauth_access_token');
			deleteCookie('oauth_refresh_token');
			deleteCookie('oauth_user');

			// Actualizar estado del AuthService
			auth.isAuthenticated.set(true);

			try {
				const user = JSON.parse(userJson);
				auth.currentUser.set(user);
			} catch {
				auth.currentUser.set(null);
			}

			// No necesitamos redirigir, ya estamos en el dashboard correcto
			return true;
		} catch (error) {
			console.error('Error procesando tokens OAuth:', error);
			// Limpiar cookies en caso de error
			deleteCookie('oauth_access_token');
			deleteCookie('oauth_refresh_token');
			deleteCookie('oauth_user');
		}
	}

	// Verificación normal de autenticación
	if (auth.isAuthenticated()) {
		return true;
	}

	// No autenticado, redirigir al login
	router.navigateByUrl('/auth/admin-login');
	return false;
};
