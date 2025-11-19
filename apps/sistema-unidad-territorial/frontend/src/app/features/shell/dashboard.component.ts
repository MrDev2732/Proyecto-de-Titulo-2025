import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../shared/auth/auth.service';
import { LoadingStateComponent } from '../../shared/components/loading-state.component';
import { WelcomeAnimationComponent } from '../../shared/components/welcome-animation.component';
import { RegistrationRequestsListComponent } from '../../shared/components/registration-requests-list.component';
import { CommunityReservationsListComponent } from '../reservations/community-reservations-list.component';
import { SpacesManagementComponent } from '../spaces/spaces-management.component';
import { NewsManagementComponent } from '../news/news-management.component';
import { ProjectsManagementComponent } from '../projects/projects-management.component';

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
	imports: [CommonModule, LoadingStateComponent, WelcomeAnimationComponent, RegistrationRequestsListComponent, CommunityReservationsListComponent, SpacesManagementComponent, NewsManagementComponent, ProjectsManagementComponent],
	templateUrl: './dashboard.component.html',
	styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
	private readonly auth = inject(AuthService);
	private readonly router = inject(Router);

	// Estados reactivos
	currentUser = this.auth.currentUser;
	isLoading = signal(false);
	errorMessage = signal<string | null>(null);

	// Datos del dashboard
	stats = signal<DashboardStats | null>(null);

	// Módulos y acciones rápidas
	modules = signal<DashboardModule[]>([]);
	quickActions = signal<QuickAction[]>([]);

	// Vista actual del dashboard
	currentView = signal<'overview' | 'registration' | 'reservations' | 'spaces' | 'news' | 'projects' | 'residents' | 'documents' | 'meetings'>('overview');

	// Control de animación de bienvenida
	showWelcomeAnimation = signal(true);

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
				status: 'active'
			},
			{
				id: 'spaces',
				title: 'Gestión de Espacios',
				description: 'Administra los espacios reservables de la comunidad',
				icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
				status: 'active'
			},
			{
				id: 'reservations',
				title: 'Gestión de Reservas',
				description: 'Aprueba y administra las reservas de espacios comunitarios',
				icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
				status: 'active'
			},
			{
				id: 'news',
				title: 'Gestión de Noticias',
				description: 'Crea y administra noticias y avisos de la comunidad',
				icon: 'M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z',
				status: 'active'
			},
			{
				id: 'projects',
				title: 'Proyectos Comunitarios',
				description: 'Administra proyectos e iniciativas de la comunidad',
				icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
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
				id: 'manage-spaces',
				title: 'Gestionar Espacios',
				description: 'Crear y configurar espacios',
				icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
				action: () => this.navigateToModule('spaces'),
				color: 'gray'
			},
			{
				id: 'manage-reservations',
				title: 'Gestionar Reservas',
				description: 'Aprobar reservas pendientes',
				icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
				action: () => this.navigateToModule('reservations'),
				color: 'gray'
			},
			{
				id: 'manage-news',
				title: 'Gestionar Noticias',
				description: 'Crear y publicar noticias',
				icon: 'M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z',
				action: () => this.navigateToModule('news'),
				color: 'gray'
			},
			{
				id: 'manage-projects',
				title: 'Gestionar Proyectos',
				description: 'Aprobar y gestionar proyectos',
				icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
				action: () => this.navigateToModule('projects'),
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

	async loadDashboardData(): Promise<void> {
		this.isLoading.set(true);
		this.errorMessage.set(null);

		try {
			// Solo cargar estadísticas básicas
			await this.loadStats();
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
			// const stats = await this.registrationAdminService.getRegistrationStats().toPromise();

			// Datos mock para desarrollo
			const mockStats: DashboardStats = {
				pending: 12,
				approved: 45,
				rejected: 3,
				total: 60,
				last_30_days: 18
			};

			// Simular delay de red
			await new Promise(resolve => setTimeout(resolve, 1000));
			this.stats.set(mockStats);
		} catch (error) {
			console.error('Error loading stats:', error);
			throw error;
		}
	}

	// Navegación y utilidades
	navigateToModule(moduleId: string): void {
		if (moduleId === 'registration') {
			this.currentView.set('registration');
		} else if (moduleId === 'reservations') {
			this.currentView.set('reservations');
		} else if (moduleId === 'spaces') {
			this.currentView.set('spaces');
		} else if (moduleId === 'news') {
			this.currentView.set('news');
		} else if (moduleId === 'projects') {
			this.currentView.set('projects');
		} else {
			this.showComingSoon(`Módulo ${moduleId}`);
		}
	}

	showComingSoon(featureName: string): void {
		alert(`${featureName} estará disponible próximamente.`);
	}

	getModuleStatusBadge(status: string): string {
		switch (status) {
			case 'active':
				return 'bg-green-100 text-green-800';
			case 'coming_soon':
				return 'bg-yellow-100 text-yellow-800';
			case 'disabled':
				return 'bg-gray-100 text-gray-500';
			default:
				return 'bg-gray-100 text-gray-500';
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

	private handleError(error: unknown): void {
		if (error instanceof Error) {
			this.errorMessage.set(error.message);
		} else {
			this.errorMessage.set('Ha ocurrido un error inesperado');
		}
	}

	// Utilidades para el template
	getUserDisplayName(): string {
		const user = this.currentUser();
		if (!user) return 'Usuario';

		// Usar email como nombre de usuario
		if (user.email) {
			return user.email.split('@')[0];
		}

		return 'Usuario';
	}

	onWelcomeAnimationComplete(): void {
		this.showWelcomeAnimation.set(false);
	}

	onLogoError(event: Event): void {
		const img = event.target as HTMLImageElement;
		const svg = img.parentElement?.querySelector('svg');
		if (svg) {
			img.style.display = 'none';
			svg.classList.remove('hidden');
		}
	}

	logout(): void {
		this.auth.logout();
		this.router.navigate(['/auth/admin-login']);
	}
}