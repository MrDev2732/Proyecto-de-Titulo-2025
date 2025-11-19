import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { SignupService, SignupFormData, SignupFileData, Community, Tenant } from '../../../shared/services/signup.service';

interface FormErrors {
  [key: string]: string | null;
}

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.scss']
})
export class SignupComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly signupService = inject(SignupService);
  readonly router = inject(Router);

  // Signals para el estado del componente
  isLoading = signal(false);
  isSubmitting = signal(false);
  submitSuccess = signal(false);
  submitError = signal<string | null>(null);

  // Datos para los dropdowns
  tenants = signal<Tenant[]>([]);
  communities = signal<Community[]>([]);

  // Archivos seleccionados
  selectedFiles = signal<{
    idCardFront: File | null;
    idCardBack: File | null;
    utilityBill: File | null;
    additionalFiles: File[];
  }>({
    idCardFront: null,
    idCardBack: null,
    utilityBill: null,
    additionalFiles: []
  });

  // Errores de archivos
  fileErrors = signal<FormErrors>({});

  // Formulario reactivo
  signupForm: FormGroup = this.fb.group({
    tenant_id: ['', [Validators.required]],
    community_id: ['', [Validators.required]],
    email: ['', [Validators.required, Validators.email]],
    full_name: ['', [Validators.required, Validators.minLength(2)]],
    rut: ['', [Validators.required]],
    address: ['', [Validators.required, Validators.minLength(10)]],
    phone_number: [''], // Opcional
    email_notifications_enabled: [true],
    whatsapp_notifications_enabled: [false],
    provider: ['google']
  });

  ngOnInit() {
    this.loadTenants();

    // Escuchar cambios en tenant_id para cargar comunidades
    this.signupForm.get('tenant_id')?.valueChanges.subscribe(tenantId => {
      if (tenantId) {
        this.loadCommunities(tenantId);
        this.signupForm.get('community_id')?.setValue('');
      } else {
        this.communities.set([]);
      }
    });
  }

  private async loadTenants() {
    this.isLoading.set(true);
    try {
      this.signupService.getTenants().subscribe({
        next: (tenants) => {
          this.tenants.set(tenants);
          this.isLoading.set(false);
        },
        error: (error) => {
          console.error('Error loading tenants:', error);
          this.isLoading.set(false);
        }
      });
    } catch (error) {
      console.error('Error loading tenants:', error);
      this.isLoading.set(false);
    }
  }

  private async loadCommunities(tenantId: string) {
    try {
      this.signupService.getCommunitiesByTenant(tenantId).subscribe({
        next: (communities) => {
          this.communities.set(communities);
        },
        error: (error) => {
          console.error('Error loading communities:', error);
        }
      });
    } catch (error) {
      console.error('Error loading communities:', error);
    }
  }

  // Manejo de archivos
  onFileSelected(event: Event, fileType: 'idCardFront' | 'idCardBack' | 'utilityBill' | 'additional') {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const files = Array.from(input.files);
    const currentFiles = this.selectedFiles();
    const currentErrors = this.fileErrors();

    if (fileType === 'additional') {
      // Para archivos adicionales, permitir múltiples
      const validFiles: File[] = [];
      const errors: string[] = [];

      files.forEach(file => {
        const validation = this.signupService.validateFile(file, 5, ['image/jpeg', 'image/png', 'application/pdf']);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          errors.push(`${file.name}: ${validation.error}`);
        }
      });

      this.selectedFiles.set({
        ...currentFiles,
        additionalFiles: [...currentFiles.additionalFiles, ...validFiles]
      });

      if (errors.length > 0) {
        this.fileErrors.set({
          ...currentErrors,
          ['additional']: errors.join(', ')
        });
      } else {
        const newErrors = { ...currentErrors };
        delete newErrors['additional'];
        this.fileErrors.set(newErrors);
      }
    } else {
      // Para archivos únicos
      const file = files[0];
      const allowedTypes = fileType === 'utilityBill' 
        ? ['image/jpeg', 'image/png', 'application/pdf']
        : ['image/jpeg', 'image/png'];

      const validation = this.signupService.validateFile(file, 5, allowedTypes);

      if (validation.isValid) {
        this.selectedFiles.set({
          ...currentFiles,
          [fileType]: file
        });

        // Limpiar error si existe
        const newErrors = { ...currentErrors };
        delete newErrors[fileType];
        this.fileErrors.set(newErrors);
      } else {
        this.fileErrors.set({
          ...currentErrors,
          [fileType]: validation.error || 'Error en archivo'
        });
      }
    }

    // Limpiar el input para permitir seleccionar el mismo archivo de nuevo
    input.value = '';
  }

  removeAdditionalFile(index: number) {
    const currentFiles = this.selectedFiles();
    const newAdditionalFiles = [...currentFiles.additionalFiles];
    newAdditionalFiles.splice(index, 1);

    this.selectedFiles.set({
      ...currentFiles,
      additionalFiles: newAdditionalFiles
    });
  }

  // Validación personalizada de RUT
  validateRutField() {
    const rutControl = this.signupForm.get('rut');
    if (!rutControl || !rutControl.value) return;

    const validation = this.signupService.validateRut(rutControl.value);
    if (validation.isValid && validation.formattedRut) {
      rutControl.setValue(validation.formattedRut, { emitEvent: false });
    }
  }

  // Envío del formulario
  async onSubmit() {
    if (this.signupForm.invalid) {
      this.markFormGroupTouched();
      return;
    }

    // Validar archivos requeridos
    const files = this.selectedFiles();
    if (!files.idCardFront || !files.idCardBack || !files.utilityBill) {
      this.submitError.set('Todos los archivos requeridos deben ser seleccionados');
      return;
    }

    // Validar RUT antes de enviar
    const rutValidation = this.signupService.validateRut(this.signupForm.value.rut);
    if (!rutValidation.isValid) {
      this.submitError.set(`RUT inválido: ${rutValidation.error}`);
      return;
    }

    this.isSubmitting.set(true);
    this.submitError.set(null);

    try {
      const formData: SignupFormData = {
        ...this.signupForm.value,
        rut: rutValidation.formattedRut
      };

      const fileData: SignupFileData = {
        id_card_front: files.idCardFront,
        id_card_back: files.idCardBack,
        utility_bill: files.utilityBill,
        additional_files: files.additionalFiles.length > 0 ? files.additionalFiles : undefined
      };

      this.signupService.createRegistrationRequest(formData, fileData).subscribe({
        next: (response) => {
          this.submitSuccess.set(true);
          this.isSubmitting.set(false);

          // Opcional: redirigir después de un tiempo
          setTimeout(() => {
            this.router.navigate(['/signin']);
          }, 3000);
        },
        error: (error) => {
          console.error('Error submitting registration:', error);
          this.submitError.set(
            error.error?.detail || 
            'Error al enviar la solicitud. Por favor, inténtalo de nuevo.'
          );
          this.isSubmitting.set(false);
        }
      });

    } catch (error) {
      console.error('Error submitting registration:', error);
      this.submitError.set('Error inesperado. Por favor, inténtalo de nuevo.');
      this.isSubmitting.set(false);
    }
  }

  private markFormGroupTouched() {
    Object.keys(this.signupForm.controls).forEach(key => {
      const control = this.signupForm.get(key);
      control?.markAsTouched();
    });
  }

  // Helpers para el template
  getFieldError(fieldName: string): string | null {
    const control = this.signupForm.get(fieldName);
    if (!control || !control.touched || !control.errors) return null;

    const errors = control.errors;
    if (errors['required']) return `${this.getFieldLabel(fieldName)} es requerido`;
    if (errors['email']) return 'Email no válido';
    if (errors['minlength']) return `${this.getFieldLabel(fieldName)} debe tener al menos ${errors['minlength'].requiredLength} caracteres`;
    
    return 'Campo inválido';
  }

  private getFieldLabel(fieldName: string): string {
    const labels: { [key: string]: string } = {
      tenant_id: 'Municipalidad',
      community_id: 'Comunidad',
      email: 'Email',
      full_name: 'Nombre completo',
      rut: 'RUT',
      address: 'Dirección',
      phone_number: 'Teléfono'
    };
    return labels[fieldName] || fieldName;
  }

  getFileError(fileType: string): string | null {
    return this.fileErrors()[fileType] || null;
  }
}
