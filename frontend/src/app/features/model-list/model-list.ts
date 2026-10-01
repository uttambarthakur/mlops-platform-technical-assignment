import { DatePipe, isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiClient, ModelRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-model-list',
  imports: [DatePipe, RouterLink],
  templateUrl: './model-list.html',
  styleUrl: './model-list.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelList {
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly searchTerm = signal('');
  protected readonly models = signal<ModelRecord[]>([]);
  protected readonly loading = signal(true);
  protected readonly errorMessage = signal('');
  protected readonly frameworkCount = computed(() => new Set(this.models().map((model) => model.framework)).size);
  protected readonly filteredModels = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();
    if (!query) return this.models();
    return this.models().filter((model) =>
      [model.name, model.framework, model.algorithm, ...model.tags].some((value) => value.toLowerCase().includes(query)),
    );
  });

  constructor() {
    if (isPlatformBrowser(this.platformId)) this.loadModels();
  }

  protected loadModels(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.api.getModels().subscribe({
      next: (models) => this.models.set(models),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.loading.set(false);
      },
      complete: () => this.loading.set(false),
    });
  }

  protected updateSearch(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
  }
}
