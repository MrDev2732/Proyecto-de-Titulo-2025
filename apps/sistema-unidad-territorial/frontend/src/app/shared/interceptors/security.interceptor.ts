import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { SecurityUtils } from '../utils/security.utils';

/**
 * Interceptor de seguridad que añade headers de seguridad y maneja errores
 */
@Injectable()
export class SecurityInterceptor implements HttpInterceptor {

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Generar nonce para CSP
    const nonce = SecurityUtils.generateNonce();

    // Headers de seguridad
    const secureRequest = req.clone({
      setHeaders: {
        // Prevenir CSRF
        'X-Requested-With': 'XMLHttpRequest',
        // Content Security Policy nonce
        'X-CSP-Nonce': nonce,
        // Prevenir XSS
        'X-Content-Type-Options': 'nosniff',
        // Prevenir clickjacking
        'X-Frame-Options': 'DENY',
        // Forzar HTTPS en producción
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        // Cache control para datos sensibles
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });

    // Validar URL del request
    if (!SecurityUtils.isSafeUrl(secureRequest.url)) {
      console.warn('Blocked unsafe URL:', secureRequest.url);
      return throwError(() => new Error('URL no permitida por políticas de seguridad'));
    }

    // Sanitizar body si es texto
    if (secureRequest.body && typeof secureRequest.body === 'object') {
      const sanitizedBody = this.sanitizeRequestBody(secureRequest.body);
      const sanitizedRequest = secureRequest.clone({ body: sanitizedBody });

      return next.handle(sanitizedRequest).pipe(
        catchError((error: HttpErrorResponse) => this.handleError(error))
      );
    }

    return next.handle(secureRequest).pipe(
      catchError((error: HttpErrorResponse) => this.handleError(error))
    );
  }

  /**
   * Sanitiza el body de las requests para prevenir inyecciones
   */
  private sanitizeRequestBody(body: any): any {
    if (!body) return body;

    if (typeof body === 'string') {
      return SecurityUtils.sanitizeHtml(body);
    }

    if (Array.isArray(body)) {
      return body.map(item => this.sanitizeRequestBody(item));
    }

    if (typeof body === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(body)) {
        if (typeof value === 'string') {
          // Sanitizar campos de texto
          if (key.toLowerCase().includes('email')) {
            sanitized[key] = SecurityUtils.sanitizeFormInput(value, 'email');
          } else if (key.toLowerCase().includes('search') || key.toLowerCase().includes('query')) {
            sanitized[key] = SecurityUtils.sanitizeFormInput(value, 'search');
          } else {
            sanitized[key] = SecurityUtils.sanitizeFormInput(value, 'text');
          }
        } else if (typeof value === 'object') {
          sanitized[key] = this.sanitizeRequestBody(value);
        } else {
          sanitized[key] = value;
        }
      }
      return sanitized;
    }

    return body;
  }

  /**
   * Maneja errores de HTTP de forma segura
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let sanitizedError: any = {
      status: error.status,
      statusText: error.statusText,
      url: error.url
    };

    // Sanitizar mensaje de error para prevenir XSS
    if (error.error?.detail) {
      sanitizedError.detail = SecurityUtils.escapeHtml(error.error.detail);
    }

    if (error.error?.message) {
      sanitizedError.message = SecurityUtils.escapeHtml(error.error.message);
    }

    // No exponer información sensible en producción
    const isProduction = (typeof window !== 'undefined' && window.location.hostname !== 'localhost');
    if (isProduction) {
      switch (error.status) {
        case 0:
          sanitizedError.detail = 'Error de conexión. Verifique su conexión a internet.';
          break;
        case 401:
          sanitizedError.detail = 'Su sesión ha expirado. Por favor, inicie sesión nuevamente.';
          break;
        case 403:
          sanitizedError.detail = 'No tiene permisos para realizar esta acción.';
          break;
        case 404:
          sanitizedError.detail = 'El recurso solicitado no fue encontrado.';
          break;
        case 429:
          sanitizedError.detail = 'Demasiadas solicitudes. Intente nuevamente más tarde.';
          break;
        case 500:
        case 502:
        case 503:
        case 504:
          sanitizedError.detail = 'Error del servidor. Intente nuevamente más tarde.';
          break;
        default:
          sanitizedError.detail = 'Ha ocurrido un error inesperado.';
      }
    }

    // Log de errores para debugging (sin información sensible)
    console.error('HTTP Error:', {
      status: error.status,
      url: error.url,
      timestamp: new Date().toISOString()
    });

    return throwError(() => {
      const httpError = new HttpErrorResponse({
        error: sanitizedError,
        status: error.status,
        statusText: error.statusText,
        url: error.url || undefined
      });
      return httpError;
    });
  }
}
