import { DatePipe, DecimalPipe, isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, PLATFORM_ID, signal } from '@angular/core';
import { ApiClient, MetricInput, MetricRecord, ModelRecord, VersionRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-metrics',
  imports: [DatePipe, DecimalPipe],
  templateUrl: './metrics.html',
  styleUrl: './metrics.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Metrics {
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly models = signal<ModelRecord[]>([]);
  protected readonly selectedModelId = signal<number | null>(null);
  protected readonly versions = signal<VersionRecord[]>([]);
  protected readonly selectedVersionId = signal('');
  protected readonly metrics = signal<MetricRecord[]>([]);
  protected readonly loadingModels = signal(true);
  protected readonly loadingVersions = signal(false);
  protected readonly loadingMetrics = signal(false);
  protected readonly ingesting = signal(false);
  protected readonly ingestMessage = signal('');
  protected readonly ingestError = signal('');
  protected readonly errorMessage = signal('');
  protected readonly activeCount = computed(() => this.metrics().filter((metric) => metric.monitoring_status === 'ACTIVE').length);

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.api.getModels().subscribe({
        next: (models) => {
          this.models.set(models);
          if (models.length > 0) {
            this.selectedModelId.set(models[0].id);
            this.loadMetrics(models[0].id);
            this.loadVersions(models[0].id);
          }
        },
        error: (error: unknown) => {
          this.errorMessage.set(describeApiError(error));
          this.loadingModels.set(false);
        },
        complete: () => this.loadingModels.set(false),
      });
    }
  }

  protected selectModel(event: Event): void {
    const modelId = Number((event.target as HTMLSelectElement).value);
    if (Number.isInteger(modelId) && modelId > 0) {
      this.selectedModelId.set(modelId);
      this.versions.set([]);
      this.selectedVersionId.set('');
      this.metrics.set([]);
      this.loadMetrics(modelId);
      this.loadVersions(modelId);
    }
  }

  protected selectVersion(event: Event): void {
    this.selectedVersionId.set((event.target as HTMLSelectElement).value);
  }

  protected loadVersions(modelId = this.selectedModelId()): void {
    if (modelId === null) return;
    this.loadingVersions.set(true);
    this.api.getVersions(modelId).subscribe({
      next: (versions) => {
        this.versions.set(versions);
        const selected = this.selectedVersionId();
        if (!versions.some((version) => String(version.id) === selected)) {
          this.selectedVersionId.set(versions[0] ? String(versions[0].id) : '');
        }
      },
      error: (error: unknown) => {
        this.ingestError.set(describeApiError(error));
        this.loadingVersions.set(false);
      },
      complete: () => this.loadingVersions.set(false),
    });
  }

  protected recordMetric(event: SubmitEvent): void {
    event.preventDefault();
    const modelId = this.selectedModelId();
    const versionId = Number(this.selectedVersionId());
    if (modelId === null || !versionId) return;

    const values = new FormData(event.target as HTMLFormElement);
    const metric: MetricInput = {
      metric_name: String(values.get('metric_name') ?? '').trim(),
      metric_value: Number(values.get('metric_value')),
      monitoring_status: String(values.get('monitoring_status') ?? 'ACTIVE') as 'ACTIVE' | 'INACTIVE',
    };
    const lastInference = String(values.get('last_successful_inference') ?? '');
    if (lastInference) metric.last_successful_inference = lastInference;

    this.ingesting.set(true);
    this.ingestError.set('');
    this.ingestMessage.set('');
    this.api.ingestMetrics(modelId, versionId, [metric]).subscribe({
      next: (records) => {
        this.ingestMessage.set(`Recorded ${records.length} metric for version ${versionId}.`);
        this.loadMetrics(modelId);
      },
      error: (error: unknown) => {
        this.ingestError.set(describeApiError(error));
        this.ingesting.set(false);
      },
      complete: () => this.ingesting.set(false),
    });
  }

  protected loadMetrics(modelId = this.selectedModelId()): void {
    if (modelId === null) return;
    this.loadingMetrics.set(true);
    this.errorMessage.set('');
    this.api.getMetrics(modelId).subscribe({
      next: (metrics) => this.metrics.set(metrics),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.loadingMetrics.set(false);
      },
      complete: () => this.loadingMetrics.set(false),
    });
  }

  protected metricLabel(name: string): string {
    const labels: Record<string, string> = {
      latency_ms: 'Prediction latency',
      throughput_rps: 'Throughput',
      error_rate: 'Error rate',
      quality_score: 'Quality score',
      drift_score: 'Drift score',
      availability: 'Availability',
    };
    return labels[name] ?? name.replaceAll('_', ' ');
  }

  protected metricUnit(name: string): string {
    const units: Record<string, string> = {
      latency_ms: 'ms',
      throughput_rps: 'req/s',
      error_rate: '%',
      availability: '%',
    };
    return units[name] ?? '';
  }
}
