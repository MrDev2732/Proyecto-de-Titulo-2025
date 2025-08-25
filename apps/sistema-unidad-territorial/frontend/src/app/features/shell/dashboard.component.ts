import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
	selector: 'app-dashboard',
	standalone: true,
	imports: [CommonModule],
	template: `
		<section class="text-center max-w-2xl mx-auto">
			<h2 class="text-3xl font-bold">Panel</h2>
			<p class="text-slate-300 mt-2">Has iniciado sesión correctamente.</p>
		</section>
	`,
})
export class DashboardComponent {}
