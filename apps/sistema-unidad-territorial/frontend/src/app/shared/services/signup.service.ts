import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

// Interfaces para el formulario de registro público
export interface SignupFormData {
  tenant_id: string;
  community_id: string;
  email: string;
  full_name: string;
  rut: string;
  address: string;
  phone_number?: string;
  email_notifications_enabled?: boolean;
  whatsapp_notifications_enabled?: boolean;
  provider?: string;
}

export interface SignupFileData {
  id_card_front: File;
  id_card_back: File;
  utility_bill: File;
  additional_files?: File[];
}

export interface SignupResponse {
  id: string;
  tenant_id: string;
  community_id: string;
  email: string;
  full_name?: string;
  rut?: string;
  address?: string;
  provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  attachments: Array<{
    id: string;
    url: string;
    kind: string;
  }>;
}

// Interface para obtener comunidades disponibles
export interface Community {
  id: string;
  name: string;
  description?: string;
  address?: string;
}

export interface Tenant {
  id: string;
  name: string;
  email: string;
}

@Injectable({ 
  providedIn: 'root' 
})
export class SignupService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1/registration';

  /**
   * Crear solicitud de registro con archivos
   */
  createRegistrationRequest(
    formData: SignupFormData, 
    files: SignupFileData
  ): Observable<SignupResponse> {
    const formDataToSend = new FormData();

    // Agregar campos básicos
    formDataToSend.append('tenant_id', formData.tenant_id);
    formDataToSend.append('community_id', formData.community_id);
    formDataToSend.append('email', formData.email);
    formDataToSend.append('full_name', formData.full_name);
    formDataToSend.append('rut', formData.rut);
    formDataToSend.append('address', formData.address);
    formDataToSend.append('provider', formData.provider || 'google');

    // Agregar teléfono si está presente
    if (formData.phone_number) {
      formDataToSend.append('phone_number', formData.phone_number);
    }

    // Agregar preferencias de notificaciones (siempre se envían, con valores por defecto si no están definidos)
    formDataToSend.append('email_notifications_enabled', String(formData.email_notifications_enabled ?? true));
    formDataToSend.append('whatsapp_notifications_enabled', String(formData.whatsapp_notifications_enabled ?? false));

    // Agregar archivos requeridos
    formDataToSend.append('id_card_front', files.id_card_front);
    formDataToSend.append('id_card_back', files.id_card_back);
    formDataToSend.append('utility_bill', files.utility_bill);

    // Agregar archivos adicionales si existen
    if (files.additional_files && files.additional_files.length > 0) {
      files.additional_files.forEach(file => {
        formDataToSend.append('additional_files', file);
      });
    }

    return this.http.post<SignupResponse>(`${this.baseUrl}/requests`, formDataToSend);
  }

  /**
   * Obtener lista de tenants (municipalidades) disponibles
   */
  getTenants(): Observable<Tenant[]> {
    return this.http.get<{tenants: Tenant[], total: number}>('/api/v1/tenants/').pipe(
      map(response => response.tenants)
    );
  }

  /**
   * Obtener comunidades de un tenant específico
   */
  getCommunitiesByTenant(tenantId: string): Observable<Community[]> {
    return this.http.get<{tenant: any, communities: Community[], total: number}>(`/api/v1/tenants/${tenantId}/communities`).pipe(
      map(response => response.communities)
    );
  }

  /**
   * Validar RUT chileno (función auxiliar)
   */
  validateRut(rut: string): { isValid: boolean; formattedRut?: string; error?: string } {
    // Limpiar RUT de puntos y espacios
    const cleanRut = rut.replace(/[.-\s]/g, '').toUpperCase();

    if (cleanRut.length < 8 || cleanRut.length > 9) {
      return { isValid: false, error: 'RUT debe tener entre 8 y 9 caracteres' };
    }

    const rutNumber = cleanRut.slice(0, -1);
    const checkDigit = cleanRut.slice(-1);

    // Validar que la parte numérica sea válida
    if (!/^\d+$/.test(rutNumber)) {
      return { isValid: false, error: 'La parte numérica del RUT no es válida' };
    }

    // Calcular dígito verificador
    let sum = 0;
    let multiplier = 2;

    for (let i = rutNumber.length - 1; i >= 0; i--) {
      sum += parseInt(rutNumber[i]) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }

    const remainder = sum % 11;
    const calculatedDigit = remainder === 0 ? '0' : remainder === 1 ? 'K' : (11 - remainder).toString();

    if (calculatedDigit !== checkDigit) {
      return { isValid: false, error: 'Dígito verificador del RUT no es válido' };
    }

    // Formatear RUT correctamente
    const formattedRut = `${rutNumber.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}-${checkDigit}`;

    return { isValid: true, formattedRut };
  }

  /**
   * Validar email
   */
  validateEmail(email: string): { isValid: boolean; error?: string } {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email || !email.trim()) {
      return { isValid: false, error: 'Email es requerido' };
    }

    if (!emailRegex.test(email)) {
      return { isValid: false, error: 'Formato de email no válido' };
    }

    return { isValid: true };
  }

  /**
   * Validar archivo (tamaño y tipo)
   */
  validateFile(file: File, maxSizeMB: number = 5, allowedTypes: string[] = ['image/jpeg', 'image/png', 'application/pdf']): { isValid: boolean; error?: string } {
    if (!file) {
      return { isValid: false, error: 'Archivo es requerido' };
    }

    // Validar tamaño
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      return { isValid: false, error: `El archivo no puede ser mayor a ${maxSizeMB}MB` };
    }

    // Validar tipo
    if (!allowedTypes.includes(file.type)) {
      const allowedTypesStr = allowedTypes.map(type => {
        switch(type) {
          case 'image/jpeg': return 'JPG';
          case 'image/png': return 'PNG';
          case 'application/pdf': return 'PDF';
          default: return type;
        }
      }).join(', ');
      return { isValid: false, error: `Tipo de archivo no permitido. Tipos permitidos: ${allowedTypesStr}` };
    }

    return { isValid: true };
  }
}
