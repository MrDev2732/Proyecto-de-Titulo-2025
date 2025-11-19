import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { NewsService, NewsItem, NewsCreateDto, NewsUpdateDto } from '../../shared/services/news.service';

interface Community {
  id: string;
  name: string;
  description?: string;
}

@Component({
  selector: 'app-news-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './news-management.component.html',
  styleUrls: ['./news-management.component.scss']
})
export class NewsManagementComponent implements OnInit {
  private readonly newsService = inject(NewsService);
  private readonly http = inject(HttpClient);

  // Estado del componente
  news = signal<NewsItem[]>([]);
  communities = signal<Community[]>([]);
  loading = signal<boolean>(false);
  loadingCommunities = signal<boolean>(false);
  error = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // Modales
  showCreateModal = signal<boolean>(false);
  showEditModal = signal<boolean>(false);
  showDeleteModal = signal<boolean>(false);

  // Noticia en edición/eliminación
  selectedNews = signal<NewsItem | null>(null);
  processing = signal<boolean>(false);

  // Formulario
  newsForm = {
    title: '',
    body: '',
    community_id: '',
    visible_from: '',
    visible_until: ''
  };

  ngOnInit(): void {
    this.loadNews();
    this.loadCommunities();
  }

  /**
   * Cargar todas las noticias de las comunidades del usuario
   */
  async loadNews(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.successMessage.set(null);

    try {
      const response = await this.newsService.getMyCommunitiesNews({ per_page: 50 }).toPromise();
      if (response) {
        this.news.set(response.news);
      }
    } catch (err: any) {
      console.error('Error loading news:', err);

      if (err.status === 403) {
        this.error.set('⛔ No tienes permisos para gestionar noticias.');
      } else if (err.status === 401) {
        this.error.set('❌ No estás autenticado. Por favor, inicia sesión nuevamente.');
      } else {
        this.error.set(err.error?.detail || 'Error al cargar las noticias');
      }
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Cargar comunidades del usuario
   */
  async loadCommunities(): Promise<void> {
    this.loadingCommunities.set(true);

    try {
      const response = await this.http.get<{ communities: Community[], total: number }>('/api/v1/user/communities').toPromise();
      if (response?.communities) {
        this.communities.set(response.communities);
      }
    } catch (err: any) {
      console.error('Error loading communities:', err);
    } finally {
      this.loadingCommunities.set(false);
    }
  }

  /**
   * Abrir modal de creación
   */
  openCreateModal(): void {
    this.resetForm();
    this.showCreateModal.set(true);
  }

  /**
   * Abrir modal de edición
   */
  openEditModal(newsItem: NewsItem): void {
    this.selectedNews.set(newsItem);
    this.newsForm = {
      title: newsItem.title,
      body: newsItem.body,
      community_id: newsItem.community_id,
      visible_from: newsItem.visible_from ? this.formatDateForInput(newsItem.visible_from) : '',
      visible_until: newsItem.visible_until ? this.formatDateForInput(newsItem.visible_until) : ''
    };
    this.showEditModal.set(true);
  }

  /**
   * Abrir modal de confirmación de eliminación
   */
  openDeleteModal(newsItem: NewsItem): void {
    this.selectedNews.set(newsItem);
    this.showDeleteModal.set(true);
  }

  /**
   * Cerrar todos los modales
   */
  closeModals(): void {
    this.showCreateModal.set(false);
    this.showEditModal.set(false);
    this.showDeleteModal.set(false);
    this.selectedNews.set(null);
    this.resetForm();
  }

  /**
   * Crear noticia
   */
  async createNews(): Promise<void> {
    if (!this.validateForm()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      const newsData: NewsCreateDto = {
        title: this.newsForm.title.trim(),
        body: this.newsForm.body.trim(),
        community_id: this.newsForm.community_id,
        visible_from: this.newsForm.visible_from || undefined,
        visible_until: this.newsForm.visible_until || null
      };

      await this.newsService.createNews(newsData).toPromise();

      this.successMessage.set('✅ Noticia creada exitosamente');
      this.closeModals();
      await this.loadNews();

      // Limpiar mensaje de éxito después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error creating news:', err);
      this.error.set(err.error?.detail || 'Error al crear la noticia');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Actualizar noticia
   */
  async updateNews(): Promise<void> {
    const selected = this.selectedNews();
    if (!selected || !this.validateForm()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      const newsData: NewsUpdateDto = {
        title: this.newsForm.title.trim(),
        body: this.newsForm.body.trim(),
        community_id: this.newsForm.community_id,
        visible_from: this.newsForm.visible_from || undefined,
        visible_until: this.newsForm.visible_until || null
      };

      await this.newsService.updateNews(selected.id, newsData).toPromise();

      this.successMessage.set('✅ Noticia actualizada exitosamente');
      this.closeModals();
      await this.loadNews();

      // Limpiar mensaje de éxito después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error updating news:', err);
      this.error.set(err.error?.detail || 'Error al actualizar la noticia');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Eliminar noticia
   */
  async deleteNews(): Promise<void> {
    const selected = this.selectedNews();
    if (!selected) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);

    try {
      await this.newsService.deleteNews(selected.id).toPromise();

      this.successMessage.set('✅ Noticia eliminada exitosamente');
      this.closeModals();
      await this.loadNews();

      // Limpiar mensaje de éxito después de 3 segundos
      setTimeout(() => this.successMessage.set(null), 3000);
    } catch (err: any) {
      console.error('Error deleting news:', err);
      this.error.set(err.error?.detail || 'Error al eliminar la noticia');
    } finally {
      this.processing.set(false);
    }
  }

  /**
   * Validar formulario
   */
  private validateForm(): boolean {
    if (!this.newsForm.title.trim()) {
      this.error.set('El título es requerido');
      return false;
    }

    if (!this.newsForm.body.trim()) {
      this.error.set('El contenido es requerido');
      return false;
    }

    if (!this.newsForm.community_id) {
      this.error.set('Debes seleccionar una comunidad');
      return false;
    }

    return true;
  }

  /**
   * Resetear formulario
   */
  private resetForm(): void {
    this.newsForm = {
      title: '',
      body: '',
      community_id: '',
      visible_from: '',
      visible_until: ''
    };
    this.error.set(null);
  }

  /**
   * Formatear fecha para el formato de date
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-CL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Formatear fecha para el input datetime-local
   */
  private formatDateForInput(dateString: string): string {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  /**
   * Obtener nombre de comunidad por ID
   */
  getCommunityName(communityId: string): string {
    const community = this.communities().find(c => c.id === communityId);
    return community?.name || 'Comunidad desconocida';
  }

  /**
   * Obtener clase de badge según estado de visibilidad
   */
  getVisibilityBadgeClass(newsItem: NewsItem): string {
    const now = new Date();
    const visibleFrom = newsItem.visible_from ? new Date(newsItem.visible_from) : null;
    const visibleUntil = newsItem.visible_until ? new Date(newsItem.visible_until) : null;

    if (visibleFrom && now < visibleFrom) {
      return 'bg-yellow-100 text-yellow-800';
    }

    if (visibleUntil && now > visibleUntil) {
      return 'bg-gray-100 text-gray-800';
    }

    return 'bg-green-100 text-green-800';
  }

  /**
   * Obtener texto de badge según estado de visibilidad
   */
  getVisibilityBadgeText(newsItem: NewsItem): string {
    const now = new Date();
    const visibleFrom = newsItem.visible_from ? new Date(newsItem.visible_from) : null;
    const visibleUntil = newsItem.visible_until ? new Date(newsItem.visible_until) : null;

    if (visibleFrom && now < visibleFrom) {
      return 'Programada';
    }

    if (visibleUntil && now > visibleUntil) {
      return 'Expirada';
    }

    return 'Activa';
  }
}
