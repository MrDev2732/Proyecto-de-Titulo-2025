import { Component, Input, Output, EventEmitter, inject, signal, OnInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { 
  RegistrationAdminService, 
  RegistrationRequestAdmin, 
  RegistrationRequestStatus,
  AttachmentKind,
  RegistrationDecision 
} from '../../shared/services/registration-admin.service';

@Component({
  selector: 'app-registration-detail-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <!-- Modal Backdrop -->
    @if (isOpenSignal) {
      <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[95vh] overflow-hidden">

          <!-- Modal Header -->
          <div class="flex justify-between items-center px-8 py-6 border-b border-gray-200 bg-gradient-to-r from-municipal-green/5 to-municipal-light/10">
            <div>
              <h2 class="text-2xl font-bold text-municipal-dark">Solicitud de Registro</h2>
              <p class="text-sm text-municipal-muted mt-1">
                ID: {{ request()?.id?.substring(0, 8) }}...
              </p>
            </div>
            <button 
              (click)="close()"
              class="text-gray-400 hover:text-municipal-green transition-colors p-2 rounded-lg hover:bg-gray-100"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <!-- Modal Content -->
          <div class="overflow-y-auto max-h-[calc(95vh-120px)]">
            @if (isLoading()) {
              <div class="flex justify-center items-center py-16">
                <div class="text-center">
                  <div class="animate-spin rounded-full h-12 w-12 border-4 border-municipal-green border-t-transparent mx-auto mb-4"></div>
                  <p class="text-municipal-muted">Cargando información del usuario...</p>
                </div>
              </div>
            } @else if (request()) {

              <!-- Carta de Usuario -->
              <div class="p-8">
                <!-- Estado y Header de la Carta -->
                <div class="bg-gradient-to-r from-white to-municipal-bg/30 rounded-2xl border-2 border-municipal-light/30 shadow-lg mb-8 overflow-hidden">

                  <!-- Header con Estado -->
                  <div class="px-8 py-6 bg-gradient-to-r from-municipal-green/10 to-municipal-light/20 border-b border-municipal-light/30">
                    <div class="flex justify-between items-start">
                      <div class="flex items-center space-x-4">
                        <!-- Avatar -->
                        <div class="w-16 h-16 bg-gradient-to-br from-municipal-green to-municipal-dark rounded-full flex items-center justify-center shadow-lg">
                          <span class="text-xl font-bold text-white">
                            {{ getInitials(request()!.full_name || request()!.email) }}
                          </span>
                        </div>
                        <div>
                          <h3 class="text-2xl font-bold text-municipal-dark">
                            {{ request()!.full_name || 'Sin nombre especificado' }}
                          </h3>
                          <p class="text-municipal-muted">{{ request()!.email }}</p>
                          @if (request()!.community) {
                            <p class="text-sm text-municipal-green font-medium mt-1">
                              <svg class="w-4 h-4 inline mr-1" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M12,8A4,4 0 0,0 8,12A4,4 0 0,0 12,16A4,4 0 0,0 16,12A4,4 0 0,0 12,8Z"/>
                              </svg>
                              {{ request()!.community!.name }}
                            </p>
                          }
                        </div>
                      </div>

                      <!-- Estado -->
                      <div class="text-right">
                        <span class="inline-flex px-4 py-2 rounded-full text-sm font-bold shadow-md"
                              [class]="registrationService.getStatusColor(request()!.status)">
                          {{ registrationService.getStatusLabel(request()!.status) }}
                        </span>
                        <p class="text-xs text-municipal-muted mt-2">
                          Creada: {{ registrationService.formatDate(request()!.created_at) }}
                        </p>
                        @if (request()!.decided_at) {
                          <p class="text-xs text-municipal-muted">
                            Decidida: {{ registrationService.formatDate(request()!.decided_at!) }}
                          </p>
                        }
                      </div>
                    </div>
                  </div>

                  <!-- Información Personal -->
                  <div class="px-8 py-6">
                    <h4 class="text-lg font-bold text-municipal-dark mb-6 flex items-center">
                      <svg class="w-5 h-5 mr-2 text-municipal-green" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
                      </svg>
                      Información Personal
                    </h4>

                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      <!-- RUT -->
                      <div class="bg-white/50 rounded-xl p-4 border border-municipal-light/30">
                        <label class="block text-sm font-bold text-municipal-dark mb-2">RUT</label>
                        <p class="text-lg font-medium text-municipal-text">
                          {{ request()!.rut || 'No especificado' }}
                        </p>
                      </div>

                      <!-- Dirección -->
                      <div class="bg-white/50 rounded-xl p-4 border border-municipal-light/30 md:col-span-2">
                        <label class="block text-sm font-bold text-municipal-dark mb-2">Dirección</label>
                        <p class="text-lg font-medium text-municipal-text">
                          {{ request()!.address || 'No especificada' }}
                        </p>
                      </div>

                      <!-- Proveedor -->
                      <div class="bg-white/50 rounded-xl p-4 border border-municipal-light/30">
                        <label class="block text-sm font-bold text-municipal-dark mb-2">Proveedor de Autenticación</label>
                        <div class="flex items-center">
                          @if (request()!.provider === 'google') {
                            <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24">
                              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                          }
                          <span class="text-lg font-medium text-municipal-text capitalize">
                            {{ request()!.provider }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Documentos Adjuntos -->
                <div class="bg-white rounded-2xl border-2 border-municipal-light/30 shadow-lg">
                  <div class="px-8 py-6 border-b border-municipal-light/30 bg-gradient-to-r from-municipal-green/5 to-municipal-light/10">
                    <h4 class="text-lg font-bold text-municipal-dark flex items-center">
                      <svg class="w-5 h-5 mr-2 text-municipal-green" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                      </svg>
                      Documentos Adjuntos
                      @if (request()!.attachments && request()!.attachments.length > 0) {
                        <span class="ml-2 inline-flex px-2 py-1 text-xs font-bold bg-municipal-green text-white rounded-full">
                          {{ request()!.attachments.length }}
                        </span>
                      }
                    </h4>
                  </div>

                  <div class="p-8">
                    @if (request()!.attachments && request()!.attachments.length > 0) {
                      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        @for (attachment of request()!.attachments; track attachment.id) {
                          <div class="bg-gradient-to-br from-white to-municipal-bg/20 rounded-xl border-2 border-municipal-light/30 shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden group">

                            <!-- Header del documento -->
                            <div class="px-4 py-3 bg-gradient-to-r from-municipal-green/10 to-municipal-light/20 border-b border-municipal-light/30">
                              <div class="flex justify-between items-center">
                                <h5 class="text-sm font-bold text-municipal-dark">
                                  {{ registrationService.getAttachmentKindLabel(attachment.kind) }}
                                </h5>
                                <span class="text-xs font-medium text-municipal-muted bg-white/70 px-2 py-1 rounded-full">
                                  {{ getFileExtension(attachment.url) }}
                                </span>
                              </div>
                            </div>

                            <!-- Preview del documento -->
                            <div class="p-4">
                              @if (isImageFile(attachment.url)) {
                                <div class="mb-4">
                                  <img 
                                    [src]="registrationService.getAttachmentUrl(attachment.url)" 
                                    [alt]="registrationService.getAttachmentKindLabel(attachment.kind)"
                                    class="w-full h-40 object-cover rounded-lg border-2 border-municipal-light/30 cursor-pointer hover:opacity-90 transition-all duration-300 group-hover:scale-105"
                                    (click)="openImageModal(attachment.url, registrationService.getAttachmentKindLabel(attachment.kind))"
                                    (error)="onImageError($event)"
                                  >
                                </div>
                              } @else {
                                <div class="mb-4 h-40 bg-gradient-to-br from-municipal-light/20 to-municipal-green/10 rounded-lg border-2 border-municipal-light/30 flex flex-col items-center justify-center text-municipal-muted group-hover:from-municipal-green/20 group-hover:to-municipal-light/30 transition-all duration-300">
                                  <svg class="w-16 h-16 mb-2 text-municipal-green/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                  </svg>
                                  <span class="text-sm font-medium">Documento</span>
                                </div>
                              }

                              <!-- Botones de acción -->
                              <div class="flex space-x-2">
                                <button 
                                  (click)="viewAttachment(attachment.url)"
                                  class="flex-1 px-4 py-3 text-sm font-bold text-white bg-gradient-to-r from-municipal-green to-municipal-dark rounded-lg hover:from-municipal-dark hover:to-municipal-green transition-all duration-300 shadow-md hover:shadow-lg flex items-center justify-center group"
                                >
                                  <svg class="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                  </svg>
                                  Ver
                                </button>
                                <button 
                                  (click)="downloadAttachment(attachment.url)"
                                  class="flex-1 px-4 py-3 text-sm font-bold text-municipal-dark bg-gradient-to-r from-municipal-light/30 to-municipal-bg/50 rounded-lg hover:from-municipal-light/50 hover:to-municipal-bg/70 transition-all duration-300 shadow-md hover:shadow-lg border border-municipal-light/50 flex items-center justify-center group"
                                >
                                  <svg class="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                  </svg>
                                  Descargar
                                </button>
                              </div>
                            </div>
                          </div>
                        }
                      </div>
                    } @else {
                      <div class="text-center py-12">
                        <svg class="mx-auto h-16 w-16 text-municipal-muted/50 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <h3 class="text-lg font-medium text-municipal-dark mb-2">Sin documentos adjuntos</h3>
                        <p class="text-municipal-muted">Esta solicitud no tiene documentos asociados.</p>
                      </div>
                    }
                  </div>
                </div>

                <!-- Notas de Decisión -->
                @if (request()!.decision_notes) {
                  <div class="mt-8 bg-white rounded-2xl border-2 border-municipal-light/30 shadow-lg">
                    <div class="px-8 py-6 border-b border-municipal-light/30 bg-gradient-to-r from-municipal-green/5 to-municipal-light/10">
                      <h4 class="text-lg font-bold text-municipal-dark flex items-center">
                        <svg class="w-5 h-5 mr-2 text-municipal-green" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                        </svg>
                        Notas de Decisión
                      </h4>
                    </div>
                    <div class="p-8">
                      <div class="bg-gradient-to-r from-municipal-bg/30 to-white rounded-xl p-6 border border-municipal-light/30">
                        <p class="text-municipal-text leading-relaxed">{{ request()!.decision_notes }}</p>
                      </div>
                    </div>
                  </div>
                }

                <!-- Acciones (solo si está pendiente) -->
                @if (request()!.status === RegistrationRequestStatus.PENDING) {
                  <div class="mt-8 bg-white rounded-2xl border-2 border-municipal-light/30 shadow-lg">
                    <div class="px-8 py-6 border-b border-municipal-light/30 bg-gradient-to-r from-municipal-green/5 to-municipal-light/10">
                      <h4 class="text-lg font-bold text-municipal-dark flex items-center">
                        <svg class="w-5 h-5 mr-2 text-municipal-green" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12,2A2,2 0 0,1 14,4V8A2,2 0 0,1 12,10A2,2 0 0,1 10,8V4A2,2 0 0,1 12,2M21,9V7L15,1H5C3.89,1 3,1.89 3,3V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V9M12,12A2,2 0 0,1 14,14V18A2,2 0 0,1 12,20A2,2 0 0,1 10,18V14A2,2 0 0,1 12,12Z"/>
                        </svg>
                        Acciones de Moderación
                      </h4>
                    </div>

                    <div class="p-8">
                      <!-- Notas de decisión -->
                      <div class="mb-6">
                        <label for="decision-notes" class="block text-sm font-bold text-municipal-dark mb-3">
                          Notas de Decisión 
                          <span class="text-municipal-muted font-normal">
                            {{ currentAction() === 'reject' ? '(obligatorias para rechazo)' : '(opcionales)' }}
                          </span>
                        </label>
                        <textarea
                          id="decision-notes"
                          [(ngModel)]="decisionNotes"
                          rows="4"
                          class="w-full px-4 py-3 border-2 border-municipal-light/50 rounded-xl focus:outline-none focus:ring-4 focus:ring-municipal-green/20 focus:border-municipal-green transition-all duration-300 bg-gradient-to-r from-white to-municipal-bg/20"
                          [class.border-red-500]="decisionNotesError()"
                          [class.focus:ring-red-200]="decisionNotesError()"
                          placeholder="Escribe las notas de la decisión (motivos, observaciones, etc.)..."
                        ></textarea>
                        @if (decisionNotesError()) {
                          <p class="mt-2 text-sm text-red-600 flex items-center">
                            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,17A1.5,1.5 0 0,1 10.5,15.5A1.5,1.5 0 0,1 12,14A1.5,1.5 0 0,1 13.5,15.5A1.5,1.5 0 0,1 12,17M12,10A1,1 0 0,1 13,11V15A1,1 0 0,1 12,16A1,1 0 0,1 11,15V11A1,1 0 0,1 12,10Z"/>
                            </svg>
                            {{ decisionNotesError() }}
                          </p>
                        }
                      </div>

                      <!-- Botones de acción -->
                      <div class="flex space-x-4">
                        <button 
                          (click)="approveRequest()"
                          [disabled]="isProcessing()"
                          class="flex-1 px-6 py-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl font-bold transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl flex items-center justify-center group"
                        >
                          @if (isProcessing() && currentAction() === 'approve') {
                            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Aprobando...
                          } @else {
                            <svg class="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                            Aprobar Solicitud
                          }
                        </button>

                        <button 
                          (click)="rejectRequest()"
                          [disabled]="isProcessing()"
                          class="flex-1 px-6 py-4 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-xl font-bold transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl flex items-center justify-center group"
                        >
                          @if (isProcessing() && currentAction() === 'reject') {
                            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Rechazando...
                          } @else {
                            <svg class="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                            Rechazar Solicitud
                          }
                        </button>
                      </div>
                    </div>
                  </div>
                }
              </div>

            } @else {
              <div class="text-center py-16 px-8">
                <div class="mb-6">
                  <svg class="mx-auto h-20 w-20 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
                  </svg>
                </div>
                <h3 class="text-xl font-bold text-municipal-dark mb-4">No se pudo cargar la información</h3>
                <p class="text-municipal-muted mb-6 max-w-md mx-auto">
                  Esto puede deberse a problemas de permisos, conexión o que la solicitud no exista.
                </p>
                <button 
                  (click)="loadRequestDetails()"
                  class="px-6 py-3 bg-gradient-to-r from-municipal-green to-municipal-dark text-white rounded-xl font-bold hover:from-municipal-dark hover:to-municipal-green transition-all duration-300 shadow-lg hover:shadow-xl"
                >
                  Reintentar Carga
                </button>
              </div>
            }
          </div>
        </div>
      </div>
    }

    <!-- Modal de imagen ampliada -->
    @if (imageModalOpen()) {
      <div class="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-[60] p-4" (click)="closeImageModal()">
        <div class="max-w-6xl max-h-full relative">
          <img 
            [src]="imageModalUrl()" 
            [alt]="imageModalTitle()"
            class="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
          >
          <div class="absolute top-4 right-4 bg-black/50 rounded-lg p-2">
            <button (click)="closeImageModal()" class="text-white hover:text-municipal-green transition-colors">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          <div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 rounded-lg px-4 py-2">
            <p class="text-white text-center font-medium">{{ imageModalTitle() }}</p>
          </div>
        </div>
      </div>
    }
  `
})
export class RegistrationDetailModalComponent implements OnInit {
  @Input() set requestId(value: string | null) {
    console.log('🔍 Modal requestId setter called with:', value);
    this._requestId = value;

    // Si el modal está abierto y recibimos un nuevo requestId, cargar datos inmediatamente
    if (value && this._isOpen()) {
      console.log('🔍 Loading data immediately from requestId setter');
      setTimeout(() => this.loadRequestDetails(), 0);
    }
  }
  get requestId() {
    return this._requestId;
  }
  private _requestId: string | null = null;
  @Input() set isOpen(value: boolean) {
    console.log('🔍 Modal isOpen setter called with:', value, 'requestId:', this.requestId);
    this._isOpen.set(value);
  
    // Si se está abriendo el modal y tenemos requestId, cargar datos inmediatamente
    if (value && this.requestId) {
      console.log('🔍 Loading data immediately from setter');
      setTimeout(() => this.loadRequestDetails(), 0);
    }
  }
  get isOpen() {
    return this._isOpen();
  }

  @Output() closed = new EventEmitter<void>();
  @Output() requestUpdated = new EventEmitter<RegistrationRequestAdmin>();

  readonly registrationService = inject(RegistrationAdminService);

  // Estado del componente
  private _isOpen = signal(false);

  // Getter público para el template
  get isOpenSignal() {
    return this._isOpen();
  }

  request = signal<RegistrationRequestAdmin | null>(null);
  isLoading = signal(false);
  isProcessing = signal(false);
  currentAction = signal<'approve' | 'reject' | null>(null);

  // Modal de imagen
  imageModalOpen = signal(false);
  imageModalUrl = signal('');
  imageModalTitle = signal('');

  // Formulario de decisión
  decisionNotes = '';
  decisionNotesError = signal<string | null>(null);

  // Constantes para template
  readonly RegistrationRequestStatus = RegistrationRequestStatus;
  readonly AttachmentKind = AttachmentKind;

  ngOnInit() {
    // Efecto para cargar detalles cuando se abre el modal
    effect(() => {
      if (this.requestId && this._isOpen()) {
        console.log('🔍 Effect triggered - requestId:', this.requestId, 'isOpen:', this._isOpen());
        this.loadRequestDetails();
      }
    });
  }

  loadRequestDetails() {
    if (!this.requestId) {
      console.error('❌ No requestId provided to modal');
      return;
    }

    console.log('🔍 Loading request details for ID:', this.requestId);
    this.isLoading.set(true);

    this.registrationService.getRegistrationRequestDetails(this.requestId).subscribe({
      next: (request) => {
        console.log('✅ Request details loaded successfully:', request);
        console.log('🔍 Number of attachments:', request.attachments?.length || 0);
        console.log('🔍 Attachments detail:', request.attachments);

        this.request.set(request);
        this.isLoading.set(false);
        
        // Log de las URLs que se van a mostrar
        if (request.attachments && request.attachments.length > 0) {
          request.attachments.forEach((attachment, index) => {
            const fullUrl = this.registrationService.getAttachmentUrl(attachment.url);
            console.log(`🔍 Attachment ${index + 1}:`, {
              kind: attachment.kind,
              originalUrl: attachment.url,
              fullUrl: fullUrl,
              isImage: this.isImageFile(attachment.url)
            });
          });
        }
      },
      error: (error) => {
        console.error('❌ Error loading request details:', error);
        console.error('❌ Error status:', error.status);
        console.error('❌ Error message:', error.message);
        console.error('❌ Error details:', error.error);
        this.isLoading.set(false);
      }
    });
  }

  close() {
    this._isOpen.set(false);
    this.closed.emit();
    this.resetForm();
  }

  private resetForm() {
    this.decisionNotes = '';
    this.decisionNotesError.set(null);
    this.currentAction.set(null);
    this.request.set(null);
  }

  approveRequest() {
    if (!this.validateDecisionNotes(false)) return;

    this.currentAction.set('approve');
    this.isProcessing.set(true);

    const decision: RegistrationDecision = {
      decision_notes: this.decisionNotes.trim() || undefined
    };

    this.registrationService.approveRegistrationRequest(this.requestId!, decision).subscribe({
      next: (updatedRequest) => {
        this.request.set(updatedRequest);
        this.requestUpdated.emit(updatedRequest);
        this.isProcessing.set(false);
        this.currentAction.set(null);
      },
      error: (error) => {
        console.error('Error approving request:', error);
        this.isProcessing.set(false);
        this.currentAction.set(null);
      }
    });
  }

  rejectRequest() {
    if (!this.validateDecisionNotes(true)) return;

    this.currentAction.set('reject');
    this.isProcessing.set(true);

    const decision: RegistrationDecision = {
      decision_notes: this.decisionNotes.trim()
    };

    this.registrationService.rejectRegistrationRequest(this.requestId!, decision).subscribe({
      next: (updatedRequest) => {
        this.request.set(updatedRequest);
        this.requestUpdated.emit(updatedRequest);
        this.isProcessing.set(false);
        this.currentAction.set(null);
      },
      error: (error) => {
        console.error('Error rejecting request:', error);
        this.isProcessing.set(false);
        this.currentAction.set(null);
      }
    });
  }

  private validateDecisionNotes(isRejection: boolean): boolean {
    const validation = this.registrationService.validateDecisionNotes(this.decisionNotes, isRejection);
    this.decisionNotesError.set(validation.error || null);
    return validation.isValid;
  }

  // Manejo de archivos
  isImageFile(url: string): boolean {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
    const urlLower = url.toLowerCase();
    return imageExtensions.some(ext => urlLower.includes(ext));
  }

  getFileExtension(url: string): string {
    const match = url.match(/\.([^.]+)$/);
    return match ? match[1].toUpperCase() : 'FILE';
  }

  viewAttachment(url: string) {
    const fullUrl = this.registrationService.getAttachmentUrl(url);
    window.open(fullUrl, '_blank');
  }

  downloadAttachment(url: string, kind?: AttachmentKind) {
    const kindLabel = kind ? this.registrationService.getAttachmentKindLabel(kind) : 'Documento';
    const extension = this.getFileExtension(url).toLowerCase();
  
    this.registrationService.downloadAttachment(url).subscribe({
      next: (blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `${kindLabel}.${extension}`;
        link.click();
        window.URL.revokeObjectURL(downloadUrl);
      },
      error: (error) => {
        console.error('Error downloading attachment:', error);
        alert('Error al descargar el archivo. Por favor, inténtalo de nuevo.');
      }
    });
  }

  openImageModal(url: string, title: string) {
    this.imageModalUrl.set(this.registrationService.getAttachmentUrl(url));
    this.imageModalTitle.set(title);
    this.imageModalOpen.set(true);
  }

  closeImageModal() {
    this.imageModalOpen.set(false);
    this.imageModalUrl.set('');
    this.imageModalTitle.set('');
  }

  getInitials(name: string): string {
    if (!name) return '?';
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  onImageError(event: Event) {
    const img = event.target as HTMLImageElement;
    // Ocultar la imagen que falló
    img.style.display = 'none';

    // Encontrar el contenedor padre y mostrar un placeholder
    const container = img.closest('.mb-3');
    if (container) {
      container.innerHTML = `
        <div class="h-32 bg-gray-100 rounded border flex items-center justify-center">
          <div class="text-center">
            <svg class="w-8 h-8 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
            </svg>
            <p class="text-xs text-gray-500">Error cargando imagen</p>
          </div>
        </div>
      `;
    }
  }
}
