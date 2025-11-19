import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface NewsItem {
	id: string;
	title: string;
	body: string;
	community_id: string;
	visible_from: string;
	visible_until: string | null;
	created_at: string;
	updated_at: string;
}

export interface NewsListResponse {
	news: NewsItem[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
}

export interface NewsFilters {
	page?: number;
	per_page?: number;
}

export interface NewsCreateDto {
	title: string;
	body: string;
	community_id: string;
	visible_from?: string;
	visible_until?: string | null;
}

export interface NewsUpdateDto {
	title?: string;
	body?: string;
	community_id?: string;
	visible_from?: string;
	visible_until?: string | null;
}

@Injectable({ 
	providedIn: 'root' 
})
export class NewsService {
	private readonly http = inject(HttpClient);
	private readonly baseUrl = '/api/v1/news';

	/**
	 * Obtener noticias de las comunidades del usuario autenticado
	 */
	getMyCommunitiesNews(filters: NewsFilters = {}): Observable<NewsListResponse> {
		let params = new HttpParams();

		if (filters.page) {
			params = params.set('page', filters.page.toString());
		}
		if (filters.per_page) {
			params = params.set('per_page', filters.per_page.toString());
		}

		return this.http.get<NewsListResponse>(`${this.baseUrl}/my-communities`, { params });
	}

	/**
	 * Crear una noticia nueva
	 */
	createNews(news: NewsCreateDto): Observable<NewsItem> {
		return this.http.post<NewsItem>(`${this.baseUrl}/`, news);
	}

	/**
	 * Editar una noticia existente
	 */
	updateNews(newsId: string, news: NewsUpdateDto): Observable<NewsItem> {
		return this.http.post<NewsItem>(`${this.baseUrl}/${newsId}`, news);
	}

	/**
	 * Deshabilitar una noticia (soft delete)
	 */
	deleteNews(newsId: string): Observable<void> {
		return this.http.delete<void>(`${this.baseUrl}/${newsId}`);
	}
}
