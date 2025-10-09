import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService } from '../../shared/auth/auth.service';
import { analyzeUserRoles } from '../../shared/auth/role.utils';
import { firstValueFrom } from 'rxjs';

interface NewsItem {
	id: string;
	title: string;
	body: string;
	visible_from: string;
	visible_until: string | null;
	created_at: string;
	updated_at: string;
}

interface NewsListResponse {
	news: NewsItem[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
}

interface Community {
	id: string;
	name: string;
	description: string | null;
	membership_status: string;
	joined_at: string;
}

interface UserCommunitiesResponse {
	communities: Community[];
	total: number;
}

@Component({
	selector: 'app-resident-dashboard',
	standalone: true,
	imports: [CommonModule],
	template: `
		<div class="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
			<!-- Header -->
			<header class="bg-white shadow-sm border-b border-gray-200">
				<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div class="flex justify-between items-center h-16">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<h1 class="text-xl font-semibold text-gray-900">Portal del Residente</h1>
							</div>
						</div>
						<div class="flex items-center space-x-4">
							<span class="text-sm text-gray-700">
								Bienvenido, {{ currentUser()?.email || 'Residente' }}
							</span>
							<button 
								(click)="logout()"
								class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
							>
								Cerrar Sesión
							</button>
						</div>
					</div>
				</div>
			</header>

			<!-- Main Content -->
			<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">

					<!-- News Section -->
					<div class="lg:col-span-2">
						<div class="bg-white rounded-lg shadow-sm border border-gray-200">
							<div class="px-6 py-4 border-b border-gray-200">
								<h2 class="text-lg font-semibold text-gray-900 flex items-center">
									<svg class="w-5 h-5 mr-2 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
										<path d="M19,5V7H15V5H19M9,5V11H5V5H9M19,13V19H15V13H19M9,17V19H5V17H9M21,3H13V9H21V3M11,3H3V13H11V3M21,11H13V21H21V11M11,15H3V21H11V15Z"/>
									</svg>
									Noticias y Avisos
								</h2>
							</div>
							<div class="p-6">
								<div *ngIf="loadingNews()" class="space-y-4">
									<div *ngFor="let i of [1,2,3]" class="animate-pulse">
										<div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
										<div class="h-3 bg-gray-200 rounded w-full mb-1"></div>
										<div class="h-3 bg-gray-200 rounded w-5/6"></div>
									</div>
								</div>

								<div *ngIf="!loadingNews() && news().length === 0" class="text-center py-8">
									<svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
									</svg>
									<p class="text-gray-500">No hay noticias disponibles en este momento</p>
								</div>

								<div *ngIf="!loadingNews() && news().length > 0" class="space-y-6">
									<article *ngFor="let item of news()" class="border-b border-gray-100 last:border-b-0 pb-6 last:pb-0">
										<h3 class="text-lg font-medium text-gray-900 mb-2">{{ item.title }}</h3>
										<p class="text-gray-700 mb-3 leading-relaxed">{{ item.body }}</p>
										<div class="text-sm text-gray-500">
											Publicado el {{ formatDate(item.created_at) }}
										</div>
									</article>
								</div>

								<div *ngIf="newsError()" class="text-center py-8">
									<svg class="w-12 h-12 mx-auto text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
									</svg>
									<p class="text-red-600 mb-2">Error al cargar las noticias</p>
									<button 
										(click)="loadNews()"
										class="text-sm text-blue-600 hover:text-blue-800 transition-colors"
									>
										Intentar nuevamente
									</button>
								</div>
							</div>
						</div>
					</div>

					<!-- Sidebar -->
					<div class="space-y-6">

						<!-- Certificate Download -->
						<div class="bg-white rounded-lg shadow-sm border border-gray-200">
							<div class="px-6 py-4 border-b border-gray-200">
								<h3 class="text-lg font-semibold text-gray-900 flex items-center">
									<svg class="w-5 h-5 mr-2 text-green-600" fill="currentColor" viewBox="0 0 24 24">
										<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
									</svg>
									Certificado de Residencia
								</h3>
							</div>
							<div class="p-6">
								<p class="text-gray-600 mb-4 text-sm">
									Descarga tu certificado de residencia oficial para trámites municipales.
								</p>

								<div *ngIf="!userCommunities().length" class="text-center py-4">
									<p class="text-gray-500 text-sm mb-3">
										No estás registrado en ninguna comunidad aún.
									</p>
									<button class="text-blue-600 hover:text-blue-800 text-sm transition-colors">
										Solicitar registro
									</button>
								</div>

								<div *ngIf="userCommunities().length" class="space-y-3">
									<div *ngFor="let community of userCommunities()" class="border border-gray-200 rounded-lg p-3">
										<h4 class="font-medium text-gray-900 mb-2">{{ community.name }}</h4>
										<button 
											(click)="downloadCertificate(community.id)"
											[disabled]="downloadingCertificate()"
											class="w-full bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
										>
											<span *ngIf="!downloadingCertificate()">Descargar Certificado</span>
											<span *ngIf="downloadingCertificate()" class="flex items-center justify-center">
												<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												Descargando...
											</span>
										</button>
									</div>
								</div>
							</div>
						</div>

						<!-- Quick Actions -->
						<div class="bg-white rounded-lg shadow-sm border border-gray-200">
							<div class="px-6 py-4 border-b border-gray-200">
								<h3 class="text-lg font-semibold text-gray-900">Acciones Rápidas</h3>
							</div>
							<div class="p-6">
								<div class="space-y-3">
									<button class="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
										<div class="flex items-center">
											<svg class="w-5 h-5 mr-3 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
											</svg>
											<div>
												<div class="font-medium text-gray-900">Ver Actividades</div>
												<div class="text-sm text-gray-500">Próximos eventos comunitarios</div>
											</div>
										</div>
									</button>

									<button class="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
										<div class="flex items-center">
											<svg class="w-5 h-5 mr-3 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
												<path d="M19,19H5V8H19M16,1V3H8V1H6V3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3H18V1M17,12H12V17H17V12Z"/>
											</svg>
											<div>
												<div class="font-medium text-gray-900">Reservar Espacios</div>
												<div class="text-sm text-gray-500">Canchas, salas y plazas</div>
											</div>
										</div>
									</button>

									<button class="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
										<div class="flex items-center">
											<svg class="w-5 h-5 mr-3 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,2A3,3 0 0,1 15,5V11A3,3 0 0,1 12,14A3,3 0 0,1 9,11V5A3,3 0 0,1 12,2M19,11C19,14.53 16.39,17.44 13,17.93V21H11V17.93C7.61,17.44 5,14.53 5,11H7A5,5 0 0,0 12,16A5,5 0 0,0 17,11H19Z"/>
											</svg>
											<div>
												<div class="font-medium text-gray-900">Reportar Problema</div>
												<div class="text-sm text-gray-500">Incidencias en la comunidad</div>
											</div>
										</div>
									</button>
								</div>
							</div>
						</div>

					</div>
				</div>
			</main>
		</div>
	`,
	styles: [`
		.animate-pulse {
			animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
		}

		@keyframes pulse {
			0%, 100% { opacity: 1; }
			50% { opacity: .5; }
		}

		.animate-spin {
			animation: spin 1s linear infinite;
		}

		@keyframes spin {
			from { transform: rotate(0deg); }
			to { transform: rotate(360deg); }
		}
	`]
})
export class ResidentDashboardComponent implements OnInit {
	private readonly http = inject(HttpClient);
	private readonly auth = inject(AuthService);
	private readonly router = inject(Router);

	// Signals for reactive state
	news = signal<NewsItem[]>([]);
	loadingNews = signal<boolean>(true);
	newsError = signal<boolean>(false);
	downloadingCertificate = signal<boolean>(false);
	userCommunities = signal<Community[]>([]);
	currentUser = this.auth.currentUser;

	async ngOnInit(): Promise<void> {
		// Check if user should be here
		const roleInfo = analyzeUserRoles(this.currentUser());
		if (roleInfo.hasAdminPrivileges) {
			// Admin users should go to admin dashboard
			this.router.navigateByUrl('/admin-dashboard');
			return;
		}

		// Load initial data
		await this.loadNews();
		await this.loadUserCommunities();
	}

	async loadNews(): Promise<void> {
		try {
			this.loadingNews.set(true);
			this.newsError.set(false);

			const response = await firstValueFrom(
				this.http.get<NewsListResponse>('/api/v1/news/public?page=1&per_page=10')
			);

			this.news.set(response.news);
		} catch (error) {
			console.error('Error loading news:', error);
			this.newsError.set(true);
		} finally {
			this.loadingNews.set(false);
		}
	}

	async loadUserCommunities(): Promise<void> {
		try {
			const response = await firstValueFrom(
				this.http.get<UserCommunitiesResponse>('/api/v1/user/communities')
			);

			this.userCommunities.set(response.communities);
		} catch (error) {
			console.error('Error loading user communities:', error);
			// Set empty array on error
			this.userCommunities.set([]);
		}
	}

	async downloadCertificate(communityId: string): Promise<void> {
		try {
			this.downloadingCertificate.set(true);

			const response = await firstValueFrom(
				this.http.get(`/api/v1/certificates/communities/${communityId}/download`, {
					responseType: 'blob'
				})
			);

			// Create download link
			const blob = new Blob([response], { type: 'application/pdf' });
			const url = window.URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `certificado_residencia_${new Date().toISOString().split('T')[0]}.pdf`;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			window.URL.revokeObjectURL(url);

		} catch (error) {
			console.error('Error downloading certificate:', error);
			alert('Error al descargar el certificado. Por favor, inténtalo nuevamente.');
		} finally {
			this.downloadingCertificate.set(false);
		}
	}

	formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('es-CL', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	logout(): void {
		this.auth.logout();
		this.router.navigateByUrl('/signin');
	}
}
