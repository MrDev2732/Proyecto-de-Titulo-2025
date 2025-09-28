/**
 * Utilidades de seguridad frontend para prevenir ataques XSS, 
 * validación de entradas y sanitización de datos
 */

export class SecurityUtils {
  
  /**
   * Sanitiza una cadena HTML para prevenir ataques XSS
   * Elimina scripts, eventos y elementos peligrosos
   */
  static sanitizeHtml(input: string): string {
    if (!input) return '';

    // Lista de elementos y atributos peligrosos
    const dangerousElements = /<(script|iframe|object|embed|form|meta|link)[^>]*>.*?<\/\1>/gi;
    const dangerousAttributes = /(on\w+|javascript:|vbscript:|data:text\/html)/gi;
    const dangerousProtocols = /(javascript:|vbscript:|data:text\/html|file:|about:)/gi;

    return input
      .replace(dangerousElements, '') // Eliminar elementos peligrosos
      .replace(dangerousAttributes, '') // Eliminar atributos de eventos
      .replace(dangerousProtocols, '') // Eliminar protocolos peligrosos
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Script tags adicionales
      .trim();
  }

  /**
   * Escapa caracteres HTML para mostrar texto plano de forma segura
   */
  static escapeHtml(input: string): string {
    if (!input) return '';

    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#x2F;'
    };

    return input.replace(/[&<>"'/]/g, (s) => map[s]);
  }

  /**
   * Valida que una cadena sea un email válido
   */
  static isValidEmail(email: string): boolean {
    if (!email || email.length > 254) return false;

    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    return emailRegex.test(email);
  }

  /**
   * Valida un RUT chileno
   */
  static isValidRut(rut: string): boolean {
    if (!rut) return false;

    // Limpiar el RUT
    const cleanRut = rut.replace(/[.-]/g, '').toLowerCase();

    // Verificar formato básico
    if (!/^\d{7,8}[0-9k]$/.test(cleanRut)) return false;

    const rutDigits = cleanRut.slice(0, -1);
    const checkDigit = cleanRut.slice(-1);

    // Calcular dígito verificador
    let sum = 0;
    let multiplier = 2;

    for (let i = rutDigits.length - 1; i >= 0; i--) {
      sum += parseInt(rutDigits[i]) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }

    const remainder = sum % 11;
    const calculatedCheckDigit = remainder === 0 ? '0' : remainder === 1 ? 'k' : (11 - remainder).toString();

    return checkDigit === calculatedCheckDigit;
  }

  /**
   * Valida que una cadena no contenga caracteres peligrosos
   */
  static isValidPlainText(input: string, maxLength: number = 500): boolean {
    if (!input) return true; // Permitir cadenas vacías
    if (input.length > maxLength) return false;

    // Verificar que no contenga HTML, scripts o caracteres de control
    const dangerousPatterns = [
      /<[^>]*>/g, // HTML tags
      /javascript:/gi,
      /vbscript:/gi,
      /on\w+\s*=/gi, // Event handlers
      /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/ // Control characters
    ];

    return !dangerousPatterns.some(pattern => pattern.test(input));
  }

  /**
   * Sanitiza entrada de texto para búsquedas
   */
  static sanitizeSearchInput(input: string): string {
    if (!input) return '';

    return input
      .replace(/[<>]/g, '') // Eliminar < y >
      .replace(/['"]/g, '') // Eliminar comillas
      .replace(/javascript:/gi, '') // Eliminar javascript:
      .replace(/[^\w\s@.-]/g, '') // Solo letras, números, espacios, @, ., -
      .trim()
      .substring(0, 100); // Limitar longitud
  }

  /**
   * Valida un token JWT básico (sin verificar firma)
   */
  static isValidJwtFormat(token: string): boolean {
    if (!token) return false;

    const parts = token.split('.');
    if (parts.length !== 3) return false;

    try {
      // Verificar que las partes sean base64 válidas
      atob(parts[0].replace(/-/g, '+').replace(/_/g, '/'));
      atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Genera un nonce aleatorio para CSP
   */
  static generateNonce(): string {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Valida que una URL sea segura
   */
  static isSafeUrl(url: string): boolean {
    if (!url) return false;

    try {
      const urlObj = new URL(url);
      const allowedProtocols = ['http:', 'https:', 'mailto:'];
      const allowedHosts = [
        'localhost',
        '127.0.0.1',
        window.location.hostname
      ];

      // Verificar protocolo
      if (!allowedProtocols.includes(urlObj.protocol)) return false;

      // Para URLs HTTP/HTTPS, verificar el host
      if (urlObj.protocol === 'http:' || urlObj.protocol === 'https:') {
        return allowedHosts.some(host => 
          urlObj.hostname === host || 
          urlObj.hostname.endsWith('.' + host)
        );
      }

      return true;
    } catch {
      return false;
    }
  }

  /**
   * Valida el formato de una fecha
   */
  static isValidDate(dateString: string): boolean {
    if (!dateString) return false;

    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date.getTime());
  }

  /**
   * Limpia y valida datos de entrada para formularios
   */
  static sanitizeFormInput(input: string, type: 'email' | 'text' | 'search' = 'text'): string {
    if (!input) return '';

    switch (type) {
      case 'email':
        return input.trim().toLowerCase().substring(0, 254);
      case 'search':
        return this.sanitizeSearchInput(input);
      case 'text':
      default:
        return this.escapeHtml(input.trim()).substring(0, 500);
    }
  }

  /**
   * Valida el tamaño de archivo para uploads
   */
  static isValidFileSize(file: File, maxSizeMB: number = 5): boolean {
    return file.size <= maxSizeMB * 1024 * 1024;
  }

  /**
   * Valida el tipo de archivo para uploads
   */
  static isValidFileType(file: File, allowedTypes: string[] = ['image/jpeg', 'image/png', 'application/pdf']): boolean {
    return allowedTypes.includes(file.type);
  }

  /**
   * Sanitiza nombre de archivo
   */
  static sanitizeFileName(fileName: string): string {
    if (!fileName) return '';

    return fileName
      .replace(/[^a-zA-Z0-9.-]/g, '_') // Solo letras, números, puntos y guiones
      .replace(/_{2,}/g, '_') // Reemplazar múltiples guiones bajos por uno
      .substring(0, 255); // Limitar longitud
  }
}

// Decorator para validación automática de métodos
export function Validate(validators: ((value: any) => boolean)[]): MethodDecorator {
  return function (target: any, propertyKey: string | symbol, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = function (...args: any[]) {
      // Validar argumentos
      for (let i = 0; i < args.length && i < validators.length; i++) {
        if (validators[i] && !validators[i](args[i])) {
          throw new Error(`Validation failed for argument ${i} in method ${String(propertyKey)}`);
        }
      }

      return originalMethod.apply(this, args);
    };

    return descriptor;
  };
}
