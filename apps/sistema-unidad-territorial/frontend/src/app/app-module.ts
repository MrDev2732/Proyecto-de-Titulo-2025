import { NgModule, provideBrowserGlobalErrorListeners } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule } from '@angular/router';
import { App } from './app';
import { appRoutes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from './shared/auth/auth.interceptor';

@NgModule({
	declarations: [App],
	imports: [BrowserModule, RouterModule.forRoot(appRoutes)],
	providers: [
		provideBrowserGlobalErrorListeners(),
		provideHttpClient(withInterceptors([authInterceptor])),
	],
	bootstrap: [App],
})
export class AppModule {}
