import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../shared/auth/auth.service';
import { HttpErrorResponse } from '@angular/common/http';
import { PasswordResetModalComponent } from '../../../shared/components/password-reset-modal.component';

interface SigninFormGroup {
	email: FormControl<string>;
	password: FormControl<string>;
	remember: FormControl<boolean>;
}

function isErrorWithMessage(value: unknown): value is { message?: string } {
	return typeof value === 'object' && value !== null && 'message' in value;
}

@Component({
	selector: 'app-signin',
	standalone: true,
	imports: [CommonModule, ReactiveFormsModule, PasswordResetModalComponent],
	templateUrl: './signin.component.html',
	styleUrl: './signin.component.scss',
})
export class SigninComponent {
	private readonly auth = inject(AuthService);
	private readonly router = inject(Router);

	isSubmitting = signal(false);
	errorMessage = signal<string | null>(null);
	passwordVisible = signal(false);
	showPasswordResetModal = signal(false);

	form = new FormGroup<SigninFormGroup>({
		email: new FormControl<string>('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
		password: new FormControl<string>('', { nonNullable: true, validators: [Validators.required] }),
		remember: new FormControl<boolean>(true, { nonNullable: true }),
	});

	async submit(): Promise<void> {
		this.errorMessage.set(null);
		if (this.form.invalid) {
			this.form.markAllAsTouched();
			return;
		}
		this.isSubmitting.set(true);
		try {
			const { email, password, remember } = this.form.getRawValue();
			await this.auth.signin({ email, password, remember });
			await this.router.navigateByUrl('/admin-dashboard');
		} catch (err: unknown) {
			let msg = 'No se pudo iniciar sesión';
			if (err instanceof HttpErrorResponse) {
				// Manejar errores específicos del backend
				if (err.status === 400) {
					msg = err.error?.detail ?? 'Email o contraseña incorrectos';
				} else if (err.status === 422) {
					msg = 'Los datos ingresados no son válidos';
				} else if (err.status === 500) {
					msg = 'Error interno del servidor. Intenta nuevamente.';
				} else if (err.status === 0) {
					msg = 'No se puede conectar al servidor. Verifica tu conexión.';
				} else {
					msg = err.error?.detail ?? err.message ?? `Error ${err.status}: ${msg}`;
				}
			} else if (isErrorWithMessage(err) && err.message) {
				msg = err.message;
			}
			this.errorMessage.set(msg);
		} finally {
			this.isSubmitting.set(false);
		}
	}

	togglePassword(): void {
		this.passwordVisible.update((v) => !v);
	}

	navigateToSignup(): void {
		this.router.navigateByUrl('/signup');
	}

	openPasswordResetModal(): void {
		this.showPasswordResetModal.set(true);
	}

	closePasswordResetModal(): void {
		this.showPasswordResetModal.set(false);
	}

		signinWithGoogle(): void {
		// Solución temporal: El backend redirigirá al frontend después del OAuth
		const frontendDashboard = `${window.location.origin}/admin-dashboard`;

		// Enviar la URL del dashboard para que el backend redirija después del OAuth exitoso
		window.location.href = `/api/v1/auth/google/login?frontend_redirect=${encodeURIComponent(frontendDashboard)}`;
	}

	onImageError(event: Event): void {
		// Ocultar la imagen que falló y mostrar el SVG fallback
		const imgElement = event.target as HTMLImageElement;
		const parentElement = imgElement.parentElement;

		if (parentElement) {
			// Ocultar la imagen
			imgElement.style.display = 'none';

			// Mostrar el SVG fallback
			const fallbackSvg = parentElement.querySelector('svg');
			if (fallbackSvg) {
				fallbackSvg.classList.remove('hidden');
			}
		}
	}
}
