import { Component, inject, signal, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule, Validators, AbstractControl } from '@angular/forms';
import { AuthService } from '../auth/auth.service';
import { HttpErrorResponse } from '@angular/common/http';

// Tipos para los diferentes pasos del flujo
type PasswordResetStep = 'request' | 'validate' | 'confirm' | 'success';

interface RequestFormGroup {
	email: FormControl<string>;
}

interface ValidateFormGroup {
	code: FormControl<string>;
}

interface ConfirmFormGroup {
	newPassword: FormControl<string>;
	confirmPassword: FormControl<string>;
}

function isErrorWithMessage(value: unknown): value is { message?: string } {
	return typeof value === 'object' && value !== null && 'message' in value;
}

@Component({
	selector: 'app-password-reset-modal',
	standalone: true,
	imports: [CommonModule, ReactiveFormsModule],
	template: `
		<!-- Modal Backdrop -->
		<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in" 
			 (click)="onBackdropClick($event)">

			<!-- Modal Container -->
			<div class="relative w-full max-w-md transform transition-all duration-300 animate-scale-in"
				 (click)="$event.stopPropagation()">

				<!-- Modal Panel -->
				<div class="password-reset-modal-panel p-8">
					<!-- Header -->
					<header class="mb-8 text-center">
						<div class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-municipal-green to-municipal-dark rounded-2xl flex items-center justify-center">
							<svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
								<path d="M18,8h-1V6c0-2.76-2.24-5-5-5S7,3.24,7,6v2H6c-1.1,0-2,0.9-2,2v10c0,1.1,0.9,2,2,2h12c1.1,0,2-0.9,2-2V10C20,8.9,19.1,8,18,8z M12,17c-1.1,0-2-0.9-2-2s0.9-2,2-2s2,0.9,2,2S13.1,17,12,17z M15.1,8H8.9V6c0-1.71,1.39-3.1,3.1-3.1s3.1,1.39,3.1,3.1V8z"/>
							</svg>
						</div>
						<h2 class="text-2xl font-bold text-municipal-dark mb-2">
							{{ getStepTitle() }}
						</h2>
						<p class="text-municipal-text text-sm">
							{{ getStepDescription() }}
						</p>
					</header>

					<!-- Close Button -->
					<button 
						type="button"
						(click)="closeModal()"
						class="absolute top-4 right-4 w-8 h-8 rounded-lg bg-municipal-light/20 hover:bg-municipal-light/40 text-municipal-muted hover:text-municipal-dark transition-all duration-200 flex items-center justify-center"
					>
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
							<path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
						</svg>
					</button>

					<!-- Step Indicator -->
					<div class="flex justify-center mb-8">
						<div class="flex items-center space-x-2">
							<div class="step-indicator" [class.active]="currentStep() === 'request'" [class.completed]="isStepCompleted('request')">1</div>
							<div class="step-line" [class.completed]="isStepCompleted('request')"></div>
							<div class="step-indicator" [class.active]="currentStep() === 'validate'" [class.completed]="isStepCompleted('validate')">2</div>
							<div class="step-line" [class.completed]="isStepCompleted('validate')"></div>
							<div class="step-indicator" [class.active]="currentStep() === 'confirm'" [class.completed]="isStepCompleted('confirm')">3</div>
						</div>
					</div>

					<!-- Step 1: Solicitar código -->
					<div *ngIf="currentStep() === 'request'" class="space-y-6">
						<form [formGroup]="requestForm" (ngSubmit)="requestReset()" class="space-y-6">
							<div class="space-y-3">
								<label for="email" class="block text-sm font-semibold text-municipal-dark">
									Email
								</label>
								<div class="relative group">
									<input
										id="email"
										type="email"
										autocomplete="email"
										formControlName="email"
										class="modal-input"
										placeholder="admin@municipalidad.cl"
										[attr.aria-invalid]="requestForm.controls.email.invalid && requestForm.controls.email.touched"
									/>
								</div>
								<div class="error-message" *ngIf="requestForm.controls.email.invalid && requestForm.controls.email.touched">
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
										<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
									</svg>
									Ingresa un email válido.
								</div>
							</div>

							<button 
								type="submit" 
								[disabled]="isSubmitting()" 
								class="modal-button"
							>
								<div class="flex items-center justify-center gap-3">
									<div class="w-5 h-5" *ngIf="!isSubmitting()">
										<svg fill="currentColor" viewBox="0 0 24 24">
											<path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
										</svg>
									</div>
									<div class="w-5 h-5" *ngIf="isSubmitting()">
										<svg class="animate-spin" fill="currentColor" viewBox="0 0 24 24">
											<path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
										</svg>
									</div>
									<span>{{ isSubmitting() ? 'Enviando...' : 'Enviar Código' }}</span>
								</div>
							</button>
						</form>
					</div>

					<!-- Step 2: Validar código -->
					<div *ngIf="currentStep() === 'validate'" class="space-y-6">
						<div class="text-center p-4 bg-municipal-green/10 rounded-xl">
							<p class="text-sm text-municipal-dark">
								Código enviado a: <strong>{{ userEmail() }}</strong>
							</p>
							<p class="text-xs text-municipal-muted mt-1">
								Revisa tu bandeja de entrada y spam
							</p>
						</div>

						<form [formGroup]="validateForm" (ngSubmit)="validateCode()" class="space-y-6">
							<div class="space-y-3">
								<label for="code" class="block text-sm font-semibold text-municipal-dark">
									Código de 6 dígitos
								</label>
								<div class="relative group">
									<input
										id="code"
										type="text"
										maxlength="6"
										formControlName="code"
										class="modal-input text-center text-2xl font-mono tracking-widest"
										placeholder="000000"
										[attr.aria-invalid]="validateForm.controls.code.invalid && validateForm.controls.code.touched"
									/>
								</div>
								<div class="error-message" *ngIf="validateForm.controls.code.invalid && validateForm.controls.code.touched">
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
										<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
									</svg>
									Ingresa el código de 6 dígitos.
								</div>
							</div>

							<div class="flex gap-3">
								<button 
									type="button"
									(click)="goBack()"
									class="modal-button-secondary flex-1"
								>
									Volver
								</button>
								<button 
									type="submit" 
									[disabled]="isSubmitting()" 
									class="modal-button flex-1"
								>
									<div class="flex items-center justify-center gap-3">
										<div class="w-5 h-5" *ngIf="!isSubmitting()">
											<svg fill="currentColor" viewBox="0 0 24 24">
												<path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
											</svg>
										</div>
										<div class="w-5 h-5" *ngIf="isSubmitting()">
											<svg class="animate-spin" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
											</svg>
										</div>
										<span>{{ isSubmitting() ? 'Validando...' : 'Validar' }}</span>
									</div>
								</button>
							</div>
						</form>

						<div class="text-center">
							<button 
								type="button"
								(click)="resendCode()"
								class="text-sm text-municipal-green hover:text-municipal-dark hover:underline transition-colors"
							>
								¿No recibiste el código? Reenviar
							</button>
						</div>
					</div>

					<!-- Step 3: Nueva contraseña -->
					<div *ngIf="currentStep() === 'confirm'" class="space-y-6">
						<form [formGroup]="confirmForm" (ngSubmit)="confirmReset()" class="space-y-6">
							<div class="space-y-3">
								<label for="newPassword" class="block text-sm font-semibold text-municipal-dark">
									Nueva Contraseña
								</label>
								<div class="relative group">
									<input
										id="newPassword"
										[type]="newPasswordVisible() ? 'text' : 'password'"
										formControlName="newPassword"
										class="modal-input pr-12"
										placeholder="••••••••••••"
										[attr.aria-invalid]="confirmForm.controls.newPassword.invalid && confirmForm.controls.newPassword.touched"
									/>
									<button 
										type="button" 
										(click)="toggleNewPasswordVisibility()" 
										class="absolute inset-y-0 right-0 px-3 text-municipal-muted hover:text-municipal-green transition-colors"
									>
										<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" *ngIf="!newPasswordVisible()">
											<path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
										</svg>
										<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" *ngIf="newPasswordVisible()">
											<path d="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.09L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.76,7.13 11.37,7 12,7Z"/>
										</svg>
									</button>
								</div>
								<div class="error-message" *ngIf="confirmForm.controls.newPassword.invalid && confirmForm.controls.newPassword.touched">
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
										<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
									</svg>
									La contraseña debe tener al menos 8 caracteres.
								</div>
							</div>

							<div class="space-y-3">
								<label for="confirmPassword" class="block text-sm font-semibold text-municipal-dark">
									Confirmar Contraseña
								</label>
								<div class="relative group">
									<input
										id="confirmPassword"
										[type]="confirmPasswordVisible() ? 'text' : 'password'"
										formControlName="confirmPassword"
										class="modal-input pr-12"
										placeholder="••••••••••••"
										[attr.aria-invalid]="confirmForm.controls.confirmPassword.invalid && confirmForm.controls.confirmPassword.touched"
									/>
									<button 
										type="button" 
										(click)="toggleConfirmPasswordVisibility()" 
										class="absolute inset-y-0 right-0 px-3 text-municipal-muted hover:text-municipal-green transition-colors"
									>
										<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" *ngIf="!confirmPasswordVisible()">
											<path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
										</svg>
										<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" *ngIf="confirmPasswordVisible()">
											<path d="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.09L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.76,7.13 11.37,7 12,7Z"/>
										</svg>
									</button>
								</div>
								<div class="error-message" *ngIf="confirmForm.controls.confirmPassword.invalid && confirmForm.controls.confirmPassword.touched">
									<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
										<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
									</svg>
									Las contraseñas no coinciden.
								</div>
							</div>

							<div class="flex gap-3">
								<button 
									type="button"
									(click)="goBack()"
									class="modal-button-secondary flex-1"
								>
									Volver
								</button>
								<button 
									type="submit" 
									[disabled]="isSubmitting()" 
									class="modal-button flex-1"
								>
									<div class="flex items-center justify-center gap-3">
										<div class="w-5 h-5" *ngIf="!isSubmitting()">
											<svg fill="currentColor" viewBox="0 0 24 24">
												<path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
											</svg>
										</div>
										<div class="w-5 h-5" *ngIf="isSubmitting()">
											<svg class="animate-spin" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z"/>
											</svg>
										</div>
										<span>{{ isSubmitting() ? 'Cambiando...' : 'Cambiar Contraseña' }}</span>
									</div>
								</button>
							</div>
						</form>
					</div>

					<!-- Step 4: Éxito -->
					<div *ngIf="currentStep() === 'success'" class="text-center space-y-6">
						<div class="w-20 h-20 mx-auto bg-green-100 rounded-full flex items-center justify-center">
							<svg class="w-10 h-10 text-green-600" fill="currentColor" viewBox="0 0 24 24">
								<path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
							</svg>
						</div>
						<div>
							<h3 class="text-xl font-bold text-municipal-dark mb-2">¡Contraseña Actualizada!</h3>
							<p class="text-municipal-text">
								Tu contraseña ha sido cambiada exitosamente. Ya puedes iniciar sesión con tu nueva contraseña.
							</p>
						</div>
						<button 
							type="button"
							(click)="closeModal()"
							class="modal-button w-full"
						>
							Continuar
						</button>
					</div>

					<!-- Error Message -->
					<div *ngIf="errorMessage()" class="mt-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-800 rounded-lg">
						<div class="flex items-start gap-3">
							<svg class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 24 24">
								<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
							</svg>
							<div>
								<h4 class="font-semibold text-red-900 mb-1">Error</h4>
								<p class="text-sm">{{ errorMessage() }}</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`,
	styles: [`
		:host {
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			z-index: 9999;
		}

		.animate-fade-in {
			animation: fadeIn 0.3s ease-out;
		}

		.animate-scale-in {
			animation: scaleIn 0.3s ease-out;
		}

		@keyframes fadeIn {
			from { opacity: 0; }
			to { opacity: 1; }
		}

		@keyframes scaleIn {
			from { 
				opacity: 0; 
				transform: scale(0.95) translateY(10px); 
			}
			to { 
				opacity: 1; 
				transform: scale(1) translateY(0); 
			}
		}
	`]
})
export class PasswordResetModalComponent {
	private readonly authService = inject(AuthService);

	// Outputs
	closed = output<void>();

	// Signals
	currentStep = signal<PasswordResetStep>('request');
	isSubmitting = signal(false);
	errorMessage = signal<string | null>(null);
	userEmail = signal<string>('');
	resetCode = signal<string>('');
	newPasswordVisible = signal(false);
	confirmPasswordVisible = signal(false);

	// Forms
	requestForm = new FormGroup<RequestFormGroup>({
		email: new FormControl<string>('', { nonNullable: true, validators: [Validators.required, Validators.email] })
	});

	validateForm = new FormGroup<ValidateFormGroup>({
		code: new FormControl<string>('', { nonNullable: true, validators: [Validators.required, Validators.minLength(6), Validators.maxLength(6)] })
	});

	confirmForm = new FormGroup<ConfirmFormGroup>({
		newPassword: new FormControl<string>('', { nonNullable: true, validators: [Validators.required, Validators.minLength(8)] }),
		confirmPassword: new FormControl<string>('', { nonNullable: true, validators: [Validators.required, Validators.minLength(8)] })
	});

	constructor() {
		// Validador personalizado para confirmar contraseñas
		this.confirmForm.addValidators(this.passwordMatchValidator);
	}

	// Validador personalizado
	private passwordMatchValidator = (control: AbstractControl) => {
		const group = control as FormGroup;
		const newPassword = group.get('newPassword')?.value;
		const confirmPassword = group.get('confirmPassword')?.value;
		return newPassword === confirmPassword ? null : { passwordMismatch: true };
	};

	getStepTitle(): string {
		switch (this.currentStep()) {
			case 'request': return 'Recuperar Contraseña';
			case 'validate': return 'Validar Código';
			case 'confirm': return 'Nueva Contraseña';
			case 'success': return 'Contraseña Actualizada';
			default: return '';
		}
	}

	getStepDescription(): string {
		switch (this.currentStep()) {
			case 'request': return 'Ingresa tu email para recibir un código de recuperación';
			case 'validate': return 'Ingresa el código de 6 dígitos que enviamos a tu email';
			case 'confirm': return 'Crea una nueva contraseña segura para tu cuenta';
			case 'success': return 'Tu contraseña ha sido actualizada exitosamente';
			default: return '';
		}
	}

	isStepCompleted(step: PasswordResetStep): boolean {
		const steps: PasswordResetStep[] = ['request', 'validate', 'confirm', 'success'];
		const currentIndex = steps.indexOf(this.currentStep());
		const stepIndex = steps.indexOf(step);
		return currentIndex > stepIndex;
	}

	async requestReset(): Promise<void> {
		this.errorMessage.set(null);
		if (this.requestForm.invalid) {
			this.requestForm.markAllAsTouched();
			return;
		}

		this.isSubmitting.set(true);
		try {
			const { email } = this.requestForm.getRawValue();
			await this.authService.requestPasswordReset(email);
			this.userEmail.set(email);
			this.currentStep.set('validate');
		} catch (err: unknown) {
			this.handleError(err);
		} finally {
			this.isSubmitting.set(false);
		}
	}

	async validateCode(): Promise<void> {
		this.errorMessage.set(null);
		if (this.validateForm.invalid) {
			this.validateForm.markAllAsTouched();
			return;
		}

		this.isSubmitting.set(true);
		try {
			const { code } = this.validateForm.getRawValue();
			await this.authService.validateResetCode(this.userEmail(), code);
			this.resetCode.set(code);
			this.currentStep.set('confirm');
		} catch (err: unknown) {
			this.handleError(err);
		} finally {
			this.isSubmitting.set(false);
		}
	}

	async confirmReset(): Promise<void> {
		this.errorMessage.set(null);
		if (this.confirmForm.invalid) {
			this.confirmForm.markAllAsTouched();
			return;
		}

		this.isSubmitting.set(true);
		try {
			const { newPassword } = this.confirmForm.getRawValue();
			await this.authService.confirmPasswordReset(this.userEmail(), this.resetCode(), newPassword);
			this.currentStep.set('success');
		} catch (err: unknown) {
			this.handleError(err);
		} finally {
			this.isSubmitting.set(false);
		}
	}

	async resendCode(): Promise<void> {
		try {
			await this.authService.requestPasswordReset(this.userEmail());
			// Mostrar mensaje de éxito temporal
		} catch (err: unknown) {
			this.handleError(err);
		}
	}

	goBack(): void {
		const steps: PasswordResetStep[] = ['request', 'validate', 'confirm'];
		const currentIndex = steps.indexOf(this.currentStep());
		if (currentIndex > 0) {
			this.currentStep.set(steps[currentIndex - 1]);
			this.errorMessage.set(null);
		}
	}

	toggleNewPasswordVisibility(): void {
		this.newPasswordVisible.update(v => !v);
	}

	toggleConfirmPasswordVisibility(): void {
		this.confirmPasswordVisible.update(v => !v);
	}

	closeModal(): void {
		this.closed.emit();
	}

	onBackdropClick(event: Event): void {
		if (event.target === event.currentTarget) {
			this.closeModal();
		}
	}

	private handleError(err: unknown): void {
		let msg = 'Ha ocurrido un error inesperado';
		if (err instanceof HttpErrorResponse) {
			if (err.status === 400) {
				msg = err.error?.detail ?? 'Datos inválidos o código incorrecto';
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
	}
}
