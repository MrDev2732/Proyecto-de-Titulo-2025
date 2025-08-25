import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, from, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
	const auth = inject(AuthService);
	const token = auth.getAccessToken();
	const cloned = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

	return next(cloned).pipe(
		catchError((error: HttpErrorResponse) => {
			if (error.status === 401) {
				return from(auth.refresh()).pipe(
					switchMap(() => {
						const t = auth.getAccessToken();
						const retried = t ? req.clone({ setHeaders: { Authorization: `Bearer ${t}` } }) : req;
						return next(retried);
					}),
					catchError(err => {
						auth.logout();
						return throwError(() => err);
					})
				);
			}
			return throwError(() => error);
		})
	);
};
