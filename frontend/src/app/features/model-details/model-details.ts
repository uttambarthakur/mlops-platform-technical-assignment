import { isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, PLATFORM_ID, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiClient, ModelRecord, VersionComparison, VersionRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-model-details',
  imports: [RouterLink],
  templateUrl: './model-details.html',
  styleUrl: './model-details.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelDetails {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly modelId = signal<number | null>(null);
  protected readonly model = signal<ModelRecord | null>(null);
  protected readonly versions = signal<VersionRecord[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly successMessage = signal('');
  protected readonly approvalPendingId = signal<number | null>(null);
  protected readonly approvalError = signal('');
  protected readonly approvalMessage = signal('');
  protected readonly compareVersionAId = signal('');
  protected readonly compareVersionBId = signal('');
  protected readonly comparison = signal<VersionComparison | null>(null);
  protected readonly comparing = signal(false);
  protected readonly compareError = signal('');

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.route.paramMap.subscribe((params) => {
        const modelId = Number(params.get('model_id'));
        if (Number.isInteger(modelId) && modelId > 0) this.loadDetails(modelId);
      });
    }
  }

  private loadDetails(modelId: number): void {
    this.modelId.set(modelId);
    this.loading.set(true);
    this.errorMessage.set('');
    forkJoin({ model: this.api.getModel(modelId), versions: this.api.getVersions(modelId) }).subscribe({
      next: ({ model, versions }) => {
        this.model.set(model);
        this.versions.set(versions);
        this.compareVersionAId.set(versions[0] ? String(versions[0].id) : '');
        this.compareVersionBId.set(versions[1] ? String(versions[1].id) : '');
      },
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.loading.set(false);
      },
      complete: () => this.loading.set(false),
    });
  }

  protected stageVersion(event: SubmitEvent): void {
    event.preventDefault();
    const modelId = this.modelId();
    if (modelId === null) return;
    this.saving.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    this.api.uploadVersion(modelId, new FormData(event.target as HTMLFormElement)).subscribe({
      next: (version) => {
        this.successMessage.set(`Version ${version.version_number} was uploaded.`);
        this.api.getVersions(modelId).subscribe({
          next: (versions) => this.versions.set(versions),
          error: (error: unknown) => this.errorMessage.set(describeApiError(error)),
        });
      },
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.saving.set(false);
      },
      complete: () => this.saving.set(false),
    });
  }

  protected updateApproval(version: VersionRecord, approvalStatus: 'APPROVED' | 'REJECTED'): void {
    const modelId = this.modelId();
    if (modelId === null) return;
    this.approvalPendingId.set(version.id);
    this.approvalError.set('');
    this.approvalMessage.set('');
    this.api.approveVersion(modelId, version.id, approvalStatus).subscribe({
      next: (updatedVersion) => {
        this.versions.update((versions) => versions.map((item) => item.id === updatedVersion.id ? updatedVersion : item));
        this.approvalMessage.set(`Version ${updatedVersion.version_number} is ${updatedVersion.approval_status}.`);
      },
      error: (error: unknown) => {
        this.approvalError.set(describeApiError(error));
        this.approvalPendingId.set(null);
      },
      complete: () => this.approvalPendingId.set(null),
    });
  }

  protected setCompareVersionA(event: Event): void {
    this.compareVersionAId.set((event.target as HTMLSelectElement).value);
    this.comparison.set(null);
  }

  protected setCompareVersionB(event: Event): void {
    this.compareVersionBId.set((event.target as HTMLSelectElement).value);
    this.comparison.set(null);
  }

  protected compareVersions(): void {
    const modelId = this.modelId();
    const versionAId = Number(this.compareVersionAId());
    const versionBId = Number(this.compareVersionBId());
    if (modelId === null || !versionAId || !versionBId) return;
    this.comparing.set(true);
    this.compareError.set('');
    this.api.compareVersions(modelId, versionAId, versionBId).subscribe({
      next: (comparison) => this.comparison.set(comparison),
      error: (error: unknown) => {
        this.compareError.set(describeApiError(error));
        this.comparing.set(false);
      },
      complete: () => this.comparing.set(false),
    });
  }

  protected metricName(name: string): string {
    return name.replaceAll('_', ' ');
  }
}
