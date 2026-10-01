import { isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiClient, ModelRecord, VersionRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-register-deployment',
  imports: [RouterLink],
  templateUrl: './register-deployment.html',
  styleUrl: './register-deployment.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterDeployment {
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly models = signal<ModelRecord[]>([]);
  protected readonly versions = signal<VersionRecord[]>([]);
  protected readonly selectedModelId = signal('');
  protected readonly environment = signal('staging');
  protected readonly loadingModels = signal(true);
  protected readonly loadingVersions = signal(false);
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly createdDeploymentId = signal<number | null>(null);
  protected readonly eligibleVersions = computed(() => {
    const versions = this.versions();
    return this.environment() === 'production'
      ? versions.filter((version) => version.approval_status?.toUpperCase() === 'APPROVED')
      : versions;
  });

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.api.getModels().subscribe({
        next: (models) => this.models.set(models),
        error: (error: unknown) => {
          this.errorMessage.set(describeApiError(error));
          this.loadingModels.set(false);
        },
        complete: () => this.loadingModels.set(false),
      });
    }
  }

  protected selectModel(event: Event): void {
    const modelId = (event.target as HTMLSelectElement).value;
    this.selectedModelId.set(modelId);
    this.versions.set([]);
    if (!modelId) return;
    this.loadingVersions.set(true);
    this.api.getVersions(Number(modelId)).subscribe({
      next: (versions) => this.versions.set(versions),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.loadingVersions.set(false);
      },
      complete: () => this.loadingVersions.set(false),
    });
  }

  protected selectEnvironment(event: Event): void {
    this.environment.set((event.target as HTMLSelectElement).value);
  }

  protected requestDeployment(event: SubmitEvent): void {
    event.preventDefault();
    const values = new FormData(event.target as HTMLFormElement);
    this.saving.set(true);
    this.errorMessage.set('');
    this.createdDeploymentId.set(null);
    this.api.createDeployment(Number(values.get('version_id')), String(values.get('environment'))).subscribe({
      next: (deployment) => this.createdDeploymentId.set(deployment.id),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.saving.set(false);
      },
      complete: () => this.saving.set(false),
    });
  }
}
