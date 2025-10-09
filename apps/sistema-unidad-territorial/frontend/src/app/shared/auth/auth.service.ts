import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { 
	SigninRequestDto, 
	TokenResponseDto, 
	UserResponseDto,
	PasswordResetRequestDto,
	PasswordResetResponseDto,
	PasswordResetCodeValidationRequestDto,
	PasswordResetCodeValidationResponseDto,
	PasswordResetConfirmRequestDto,
	PasswordResetConfirmResponseDto
} from './auth.models';

const ACCESS_KEY = 'sut.access';
const REFRESH_KEY = 'sut.refresh';

@Injectable({ providedIn: 'root' })
export class AuthService {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = '/api/v1/auth';
	private readonly passwordResetUrl = '/api/v1/password-reset';

	isAuthenticated = signal<boolean>(false);
	currentUser = signal<UserResponseDto | null>(null);

	constructor() {
		this.restore();
	}

	getAccessToken(): string | null {
		return localStorage.getItem(ACCESS_KEY) ?? sessionStorage.getItem(ACCESS_KEY);
	}

	private restore(): void {
		const access = localStorage.getItem(ACCESS_KEY) ?? sessionStorage.getItem(ACCESS_KEY);
		const user = localStorage.getItem('sut.user') ?? sessionStorage.getItem('sut.user');
		if (access && user) {
			this.isAuthenticated.set(true);
			try { this.currentUser.set(JSON.parse(user)); } catch {
				this.currentUser.set(null);
			}
		}
	}

	async signin(req: SigninRequestDto): Promise<void> {
		const res = await firstValueFrom(
			this.http.post<TokenResponseDto>(`${this.baseUrl}/signin`, {
				email: req.email,
				password: req.password,
			})
		);

		this.persistTokens(res, req.remember ?? true);
		this.isAuthenticated.set(true);
		this.currentUser.set(res.user);
	}

	async refresh(): Promise<void> {
		const refreshToken = localStorage.getItem(REFRESH_KEY) ?? sessionStorage.getItem(REFRESH_KEY);
		if (!refreshToken) return;
		const res = await firstValueFrom(
			this.http.post<TokenResponseDto>(`${this.baseUrl}/refresh`, { refresh_token: refreshToken })
		);
		this.persistTokens(res, Boolean(localStorage.getItem(REFRESH_KEY)));
	}

	logout(): void {
		localStorage.removeItem(ACCESS_KEY);
		localStorage.removeItem(REFRESH_KEY);
		localStorage.removeItem('sut.user');
		sessionStorage.removeItem(ACCESS_KEY);
		sessionStorage.removeItem(REFRESH_KEY);
		sessionStorage.removeItem('sut.user');
		this.isAuthenticated.set(false);
		this.currentUser.set(null);
	}

	private persistTokens(res: TokenResponseDto, remember: boolean): void {
		const storage = remember ? localStorage : sessionStorage;
		storage.setItem(ACCESS_KEY, res.access_token);
		storage.setItem(REFRESH_KEY, res.refresh_token);
		storage.setItem('sut.user', JSON.stringify(res.user));
		if (remember) {
			sessionStorage.removeItem(ACCESS_KEY);
			sessionStorage.removeItem(REFRESH_KEY);
			sessionStorage.removeItem('sut.user');
		} else {
			localStorage.removeItem(ACCESS_KEY);
			localStorage.removeItem(REFRESH_KEY);
			localStorage.removeItem('sut.user');
		}
	}

	// ========================================
	// MÉTODOS PARA RECUPERACIÓN DE CONTRASEÑA
	// ========================================

	/**
	 * Solicita un código de recuperación de contraseña
	 * @param email Email del usuario
	 * @returns Respuesta con información del token de reset
	 */
	async requestPasswordReset(email: string): Promise<PasswordResetResponseDto> {
		const request: PasswordResetRequestDto = { email };
		return await firstValueFrom(
			this.http.post<PasswordResetResponseDto>(`${this.passwordResetUrl}/request`, request)
		);
	}

	/**
	 * Valida el código de recuperación de contraseña
	 * @param email Email del usuario
	 * @param code Código de 6 dígitos recibido por email
	 * @returns Token para cambiar contraseña
	 */
	async validateResetCode(email: string, code: string): Promise<PasswordResetCodeValidationResponseDto> {
		const request: PasswordResetCodeValidationRequestDto = { email, code };
		return await firstValueFrom(
			this.http.post<PasswordResetCodeValidationResponseDto>(`${this.passwordResetUrl}/validate`, request)
		);
	}

	/**
	 * Confirma el cambio de contraseña
	 * @param email Email del usuario
	 * @param code Código de 6 dígitos recibido por email
	 * @param newPassword Nueva contraseña
	 * @returns Confirmación del cambio
	 */
	async confirmPasswordReset(email: string, code: string, newPassword: string): Promise<PasswordResetConfirmResponseDto> {
		const request = { 
			email: email,
			code: code,
			new_password: newPassword
		};
		return await firstValueFrom(
			this.http.post<PasswordResetConfirmResponseDto>(`${this.passwordResetUrl}/confirm`, request)
		);
	}
}
