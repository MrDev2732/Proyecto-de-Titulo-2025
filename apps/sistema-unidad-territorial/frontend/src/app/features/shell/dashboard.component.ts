import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../shared/auth/auth.service';
import { RegistrationRequestService } from '../../shared/services/registration-request.service';
import { RegistrationRequestDto, RegistrationStatus, RegistrationProvider } from '../../shared/models/registration-request.models';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { SecurityUtils } from '../../shared/utils/security.utils';
import { LoadingStateComponent } from '../../shared/components/loading-state.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { WelcomeAnimationComponent } from '../../shared/components/welcome-animation.component';

interface DashboardStats {
	pending: number;
	approved: number;
	rejected: number;
	total: number;
	last_30_days: number;
}

interface DashboardModule {
	id: string;
	title: string;
	description: string;
	icon: string;
	path?: string;
	badge?: number;
	status: 'active' | 'coming_soon' | 'disabled';
}

interface QuickAction {
	id: string;
	title: string;
	description: string;
	icon: string;
	action: () => void;
	color: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'gray';
}

@Component({
	selector: 'app-dashboard',
	standalone: true,
	imports: [CommonModule, FormsModule, LoadingStateComponent, EmptyStateComponent, WelcomeAnimationComponent],
	templateUrl: './dashboard.component.html',
	styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
	private readonly auth = inject(AuthService);
	private readonly router = inject(Router);
	private readonly registrationService = inject(RegistrationRequestService);

	// Estados reactivos
	currentUser = this.auth.currentUser;
	isLoading = signal(false);
	isLoadingRequests = signal(false);
	isProcessingRequest = signal<string | null>(null);
	errorMessage = signal<string | null>(null);

	// Datos del dashboard
	stats = signal<DashboardStats | null>(null);
	registrationRequests = signal<RegistrationRequestDto[]>([]);
	selectedStatus = signal<RegistrationStatus | 'ALL'>('ALL');
	searchTerm = signal('');

	// Módulos y acciones rápidas
	modules = signal<DashboardModule[]>([]);
	quickActions = signal<QuickAction[]>([]);

	// Vista actual del dashboard
	currentView = signal<'overview' | 'registration' | 'residents' | 'projects' | 'documents' | 'meetings'>('overview');

	// Control de animación de bienvenida
	showWelcomeAnimation = signal(true);

	// Constantes para templates
	readonly RegistrationStatus = RegistrationStatus;
	readonly RegistrationProvider = RegistrationProvider;

	ngOnInit(): void {
		this.initializeDashboard();
	}

	private async initializeDashboard(): Promise<void> {
		this.setupModules();
		this.setupQuickActions();
		await this.loadDashboardData();
	}

	private setupModules(): void {
		const modules: DashboardModule[] = [
			{
				id: 'registration',
				title: 'Gestión de Solicitudes',
				description: 'Administra las solicitudes de registro de nuevos vecinos',
				icon: 'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z',
				badge: 12, // Número de solicitudes pendientes
				status: 'active'
			},
			{
				id: 'residents',
				title: 'Directorio de Vecinos',
				description: 'Gestiona la información de los vecinos registrados',
				icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z',
				status: 'coming_soon'
			},
			{
				id: 'projects',
				title: 'Proyectos Comunitarios',
				description: 'Administra proyectos e iniciativas de la comunidad',
				icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
				status: 'coming_soon'
			},
			{
				id: 'documents',
				title: 'Documentos y Actas',
				description: 'Gestiona documentos oficiales y actas de reuniones',
				icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
				status: 'coming_soon'
			},
			{
				id: 'meetings',
				title: 'Reuniones y Eventos',
				description: 'Programa y gestiona reuniones y eventos comunitarios',
				icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
				status: 'coming_soon'
			},
			{
				id: 'reports',
				title: 'Reportes y Estadísticas',
				description: 'Genera reportes y visualiza estadísticas de la comunidad',
				icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
				status: 'coming_soon'
			}
		];
		this.modules.set(modules);
	}

	private setupQuickActions(): void {
		const actions: QuickAction[] = [
			{
				id: 'new-resident',
				title: 'Gestionar Solicitudes',
				description: 'Revisar solicitudes pendientes',
				icon: 'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z',
				action: () => this.navigateToModule('registration'),
				color: 'gray'
			},
			{
				id: 'new-project',
				title: 'Nuevo Proyecto',
				description: 'Crear proyecto comunitario',
				icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
				action: () => this.showComingSoon('Creación de Proyectos'),
				color: 'gray'
			},
			{
				id: 'schedule-meeting',
				title: 'Programar Reunión',
				description: 'Agendar reunión o evento',
				icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
				action: () => this.showComingSoon('Programación de Reuniones'),
				color: 'gray'
			},
			{
				id: 'generate-report',
				title: 'Generar Reporte',
				description: 'Crear reporte personalizado',
				icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
				action: () => this.showComingSoon('Generación de Reportes'),
				color: 'gray'
			}
		];
		this.quickActions.set(actions);
	}

	getEmptyStateActionText(): string | undefined {
		return this.selectedStatus() !== 'ALL' ? 'Ver todas las solicitudes' : undefined;
	}

	getEmptyStateActionCallback(): (() => void) | undefined {
		if (this.selectedStatus() !== 'ALL') {
			return () => {
				this.selectedStatus.set('ALL');
				this.onStatusFilterChange();
			};
		}
		return undefined;
	}

	async loadDashboardData(): Promise<void> {
		this.isLoading.set(true);
		this.errorMessage.set(null);

		try {
			// Cargar estadísticas y solicitudes pendientes en paralelo
			await Promise.all([
				this.loadStats(),
				this.loadRegistrationRequests()
			]);
		} catch (error) {
			console.error('Error loading dashboard data:', error);
			this.handleError(error);
		} finally {
			this.isLoading.set(false);
		}
	}

	private async loadStats(): Promise<void> {
		try {
			// TODO: Reemplazar con llamada real al servicio cuando esté disponible el backend
			// const stats = await this.registrationService.getRegistrationStats().toPromise();

			// Datos mock para desarrollo
			const mockStats: DashboardStats = {
				pending: 12,
				approved: 45,
				rejected: 3,
				total: 60,
				last_30_days: 18
			};

			// Simular delay de red
			await new Promise(resolve => setTimeout(resolve, 500));
			this.stats.set(mockStats);
		} catch (error) {
			console.error('Error loading stats:', error);
			// No mostrar error por estadísticas, continuar con las solicitudes
		}
	}

	private async loadRegistrationRequests(): Promise<void> {
		this.isLoadingRequests.set(true);
		try {
			// TODO: Reemplazar con llamada real al servicio cuando esté disponible el backend
			// const filters = {
			// 	status: this.selectedStatus() === 'ALL' ? undefined : this.selectedStatus() as RegistrationStatus,
			// 	search: this.searchTerm() || undefined,
			// 	per_page: 20
			// };
			// const response = await this.registrationService.getRegistrationRequests(filters).toPromise();

			// Datos mock para desarrollo
			const mockRequests: RegistrationRequestDto[] = [
				{
					id: '1',
					tenant_id: 'tenant-1',
					community_id: 'community-1',
					email: 'maria.gonzalez@email.com',
					full_name: 'María González',
					rut: '12.345.678-9',
					address: 'Av. Los Leones 1234, Las Condes',
					provider: RegistrationProvider.EMAIL,
					status: RegistrationStatus.PENDING,
					created_at: new Date().toISOString(),
					updated_at: new Date().toISOString(),
					community: {
						id: 'community-1',
						name: 'Junta de Vecinos Villa El Sol'
					}
				},
				{
					id: '2',
					tenant_id: 'tenant-1',
					community_id: 'community-1',
					email: 'carlos.rodriguez@gmail.com',
					full_name: 'Carlos Rodríguez',
					rut: '98.765.432-1',
					address: 'Pasaje Las Flores 567',
					provider: RegistrationProvider.GOOGLE,
					status: RegistrationStatus.PENDING,
					created_at: new Date(Date.now() - 86400000).toISOString(), // 1 día atrás
					updated_at: new Date(Date.now() - 86400000).toISOString(),
					community: {
						id: 'community-1',
						name: 'Junta de Vecinos Villa El Sol'
					}
				},
				{
					id: '3',
					tenant_id: 'tenant-1',
					community_id: 'community-1',
					email: 'ana.lopez@outlook.com',
					full_name: 'Ana López',
					provider: RegistrationProvider.EMAIL,
					status: RegistrationStatus.APPROVED,
					decided_at: new Date(Date.now() - 3600000).toISOString(), // 1 hora atrás
					created_at: new Date(Date.now() - 172800000).toISOString(), // 2 días atrás
					updated_at: new Date(Date.now() - 3600000).toISOString(),
					community: {
						id: 'community-1',
						name: 'Junta de Vecinos Villa El Sol'
					}
				}
			];

			// Filtrar por estado si es necesario
			let filteredRequests = mockRequests;
			if (this.selectedStatus() !== 'ALL') {
				filteredRequests = mockRequests.filter(req => req.status === this.selectedStatus());
			}

			// Filtrar por búsqueda si es necesario
			if (this.searchTerm()) {
				const searchLower = this.searchTerm().toLowerCase();
				filteredRequests = filteredRequests.filter(req => 
					req.email.toLowerCase().includes(searchLower) ||
					(req.full_name && req.full_name.toLowerCase().includes(searchLower))
				);
			}

			// Simular delay de red
			await new Promise(resolve => setTimeout(resolve, 800));
			this.registrationRequests.set(filteredRequests);
		} catch (error) {
			console.error('Error loading registration requests:', error);
			this.handleError(error);
		} finally {
			this.isLoadingRequests.set(false);
		}
	}

	async processRequest(requestId: string, approve: boolean): Promise<void> {
		this.isProcessingRequest.set(requestId);
		this.errorMessage.set(null);

		try {
			// TODO: Reemplazar con llamada real al servicio cuando esté disponible el backend
			// const decision = {
			// 	decision: approve ? RegistrationStatus.APPROVED as const : RegistrationStatus.REJECTED as const,
			// 	decision_notes: approve ? 'Solicitud aprobada por administrador' : 'Solicitud rechazada por administrador'
			// };
			// await this.registrationService.processRegistrationRequest(requestId, decision).toPromise();

			// Simular procesamiento
			await new Promise(resolve => setTimeout(resolve, 1000));

			// Actualizar el estado local del request
			const currentRequests = this.registrationRequests();
			const updatedRequests = currentRequests.map(req => {
				if (req.id === requestId) {
					return {
						...req,
						status: approve ? RegistrationStatus.APPROVED : RegistrationStatus.REJECTED,
						decided_at: new Date().toISOString(),
						updated_at: new Date().toISOString()
					};
				}
				return req;
			});

			this.registrationRequests.set(updatedRequests);

			// Actualizar estadísticas mock
			const currentStats = this.stats();
			if (currentStats) {
				this.stats.set({
					...currentStats,
					pending: Math.max(0, currentStats.pending - 1),
					approved: approve ? currentStats.approved + 1 : currentStats.approved,
					rejected: !approve ? currentStats.rejected + 1 : currentStats.rejected
				});
			}
		} catch (error) {
			console.error('Error processing request:', error);
			this.handleError(error);
		} finally {
			this.isProcessingRequest.set(null);
		}
	}

	onStatusFilterChange(): void {
		this.loadRegistrationRequests();
	}

	onSearchChange(): void {
		// Sanitizar entrada de búsqueda para prevenir XSS
		const sanitizedSearch = SecurityUtils.sanitizeSearchInput(this.searchTerm());
		this.searchTerm.set(sanitizedSearch);

		// Debounce la búsqueda
		setTimeout(() => {
			this.loadRegistrationRequests();
		}, 300);
	}

	logout(): void {
		this.auth.logout();
		this.router.navigateByUrl('/auth/admin-login');
	}

	navigateToModule(moduleId: string): void {
		this.currentView.set(moduleId as any);
	}

	showComingSoon(feature: string): void {
		// TODO: Implementar modal o toast de "Próximamente"
		alert(`${feature} estará disponible próximamente.`);
	}

	onWelcomeAnimationComplete(): void {
		this.showWelcomeAnimation.set(false);
	}

	getUserDisplayName(): string {
		const user = this.currentUser();
		if (user?.email) {
			const emailName = user.email.split('@')[0];
			return emailName.charAt(0).toUpperCase() + emailName.slice(1);
		}
		return 'Administrador';
	}

	onLogoError(event: Event): void {
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

	getActionColorClass(color: string): string {
		// Todos los iconos usan el mismo estilo minimalista
		return 'bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors';
	}

	getModuleStatusBadge(status: string): string {
		switch (status) {
			case 'active':
				return 'bg-green-50 text-green-700 border border-green-200';
			case 'coming_soon':
				return 'bg-yellow-50 text-yellow-700 border border-yellow-200';
			case 'disabled':
				return 'bg-gray-50 text-gray-700 border border-gray-200';
			default:
				return 'bg-gray-50 text-gray-700 border border-gray-200';
		}
	}

	getModuleStatusText(status: string): string {
		switch (status) {
			case 'active':
				return 'Activo';
			case 'coming_soon':
				return 'Próximamente';
			case 'disabled':
				return 'Deshabilitado';
			default:
				return 'Desconocido';
		}
	}

	getStatusColor(status: RegistrationStatus): string {
		switch (status) {
			case RegistrationStatus.PENDING:
				return 'bg-yellow-50 text-yellow-700 border border-yellow-200';
			case RegistrationStatus.APPROVED:
				return 'bg-green-50 text-green-700 border border-green-200';
			case RegistrationStatus.REJECTED:
				return 'bg-red-50 text-red-700 border border-red-200';
			default:
				return 'bg-gray-50 text-gray-700 border border-gray-200';
		}
	}

	getProviderIcon(provider: RegistrationProvider): string {
		switch (provider) {
			case RegistrationProvider.GOOGLE:
				return '🔗'; // Google icon
			case RegistrationProvider.EMAIL:
				return '✉️'; // Email icon
			default:
				return '👤';
		}
	}

	formatDate(dateString: string): string {
		// Validar fecha antes de formatear
		if (!SecurityUtils.isValidDate(dateString)) {
			return 'Fecha inválida';
		}

		return new Date(dateString).toLocaleDateString('es-CL', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	/**
	 * Escapa HTML para mostrar texto de forma segura
	 */
	safeDisplayText(text: string | null | undefined): string {
		if (!text) return '';
		return SecurityUtils.escapeHtml(text);
	}

	/**
	 * Valida que un email sea seguro antes de mostrarlo
	 */
	safeDisplayEmail(email: string | null | undefined): string {
		if (!email) return '';
		if (!SecurityUtils.isValidEmail(email)) {
			return 'Email inválido';
		}
		return SecurityUtils.escapeHtml(email);
	}

	private handleError(error: unknown): void {
		let message = 'Ha ocurrido un error inesperado';

		if (error instanceof HttpErrorResponse) {
			if (error.status === 401) {
				message = 'Su sesión ha expirado. Por favor, inicie sesión nuevamente.';
				this.auth.logout();
				this.router.navigateByUrl('/auth/admin-login');
				return;
			} else if (error.status === 403) {
				message = 'No tiene permisos para realizar esta acción.';
			} else if (error.status >= 500) {
				message = 'Error del servidor. Intente nuevamente más tarde.';
			} else {
				message = error.error?.detail || error.message || message;
			}
		}

		this.errorMessage.set(message);
	}
}
