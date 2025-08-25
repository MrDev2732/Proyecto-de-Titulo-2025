import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { LoginRequestDto, TokenResponseDto, UserResponseDto } from './auth.models';

const ACCESS_KEY = 'sut.access';
const REFRESH_KEY = 'sut.refresh';

@Injectable({ providedIn: 'root' })
export class AuthService {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = '/api/v1/auth';

	isAuthenticated = signal<boolean>(false);
	currentUser = signal<UserResponseDto | null>(null);

	constructor() {
		this.restore();
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

	async login(req: LoginRequestDto): Promise<void> {
		const res = await firstValueFrom(
			this.http.post<TokenResponseDto>(`${this.baseUrl}/login`, {
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

	getAccessToken(): string | null {
		return localStorage.getItem(ACCESS_KEY) ?? sessionStorage.getItem(ACCESS_KEY);
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
}
