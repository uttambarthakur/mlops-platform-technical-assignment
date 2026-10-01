import { HttpClient, HttpHeaders, HttpInterceptorFn } from '@angular/common/http';
import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Observable } from 'rxjs';

export interface ModelRecord {
  id: number;
  name: string;
  framework: string;
  algorithm: string;
  tags: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface VersionRecord {
  id: number;
  model_id: number;
  version_number: number;
  artifact_uri: string;
  training_data_ref: string | null;
  approval_status: string | null;
  lifecycle_stage: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface DeploymentRecord {
  id: number;
  version_id: number;
  environment: string;
  status: string;
  artifact_uri: string;
  created_at: string | null;
}

export interface MetricRecord {
  id: number;
  version_id: number;
  metric_name: string;
  metric_value: number;
  monitoring_status: string;
  last_successful_inference: string | null;
  recorded_at: string | null;
}

export interface MetricInput {
  metric_name: string;
  metric_value: number;
  monitoring_status?: 'ACTIVE' | 'INACTIVE';
  last_successful_inference?: string | null;
}

export interface MetricDelta {
  metric_name: string;
  version_a_value: number | null;
  version_b_value: number | null;
  difference: number | null;
}

export interface VersionComparison {
  model_id: number;
  version_a: VersionRecord;
  version_b: VersionRecord;
  metric_deltas: MetricDelta[];
}

export interface HealthResponse {
  status: string;
}

const accessTokenKey = 'mlops_access_token';

export const sessionTokenInterceptor: HttpInterceptorFn = (request, next) => {
  const platformId = inject(PLATFORM_ID);
  const token = isPlatformBrowser(platformId) ? sessionStorage.getItem(accessTokenKey) : null;
  return next(token ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : request);
};

@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api/v1';

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`);
  }

  setAccessToken(token: string): void {
    if (typeof sessionStorage === 'undefined') return;
    if (token.trim()) sessionStorage.setItem(accessTokenKey, token.trim());
    else sessionStorage.removeItem(accessTokenKey);
  }

  hasAccessToken(): boolean {
    return typeof sessionStorage !== 'undefined' && sessionStorage.getItem(accessTokenKey) !== null;
  }

  getModels(): Observable<ModelRecord[]> {
    return this.http.get<ModelRecord[]>(`${this.baseUrl}/models`);
  }

  getModel(modelId: number): Observable<ModelRecord> {
    return this.http.get<ModelRecord>(`${this.baseUrl}/models/${modelId}`);
  }

  createModel(payload: Pick<ModelRecord, 'name' | 'framework' | 'algorithm' | 'tags'>): Observable<ModelRecord> {
    return this.http.post<ModelRecord>(`${this.baseUrl}/models`, payload);
  }

  getVersions(modelId: number): Observable<VersionRecord[]> {
    return this.http.get<VersionRecord[]>(`${this.baseUrl}/models/${modelId}/versions`);
  }

  approveVersion(
    modelId: number,
    versionId: number,
    approvalStatus: 'APPROVED' | 'REJECTED',
  ): Observable<VersionRecord> {
    return this.http.post<VersionRecord>(
      `${this.baseUrl}/models/${modelId}/versions/${versionId}/approval`,
      { approval_status: approvalStatus },
    );
  }

  compareVersions(modelId: number, versionAId: number, versionBId: number): Observable<VersionComparison> {
    return this.http.get<VersionComparison>(`${this.baseUrl}/models/${modelId}/versions/compare`, {
      params: { version_a_id: versionAId, version_b_id: versionBId },
    });
  }

  uploadVersion(modelId: number, formData: FormData): Observable<VersionRecord> {
    return this.http.post<VersionRecord>(`${this.baseUrl}/models/${modelId}/versions`, formData);
  }

  getDeployments(): Observable<DeploymentRecord[]> {
    return this.http.get<DeploymentRecord[]>(`${this.baseUrl}/deployments`);
  }

  createDeployment(
    versionId: number,
    environment: string,
    idempotencyKey = crypto.randomUUID(),
  ): Observable<DeploymentRecord> {
    return this.http.post<DeploymentRecord>(`${this.baseUrl}/deployments`, {
      version_id: versionId,
      environment,
    }, {
      headers: new HttpHeaders({ 'Idempotency-Key': idempotencyKey }),
    });
  }

  ingestMetrics(modelId: number, versionId: number, metrics: MetricInput[]): Observable<MetricRecord[]> {
    return this.http.post<MetricRecord[]>(
      `${this.baseUrl}/models/${modelId}/versions/${versionId}/metrics`,
      { metrics },
    );
  }

  retryDeployment(deploymentId: number): Observable<DeploymentRecord> {
    return this.http.post<DeploymentRecord>(`${this.baseUrl}/deployments/${deploymentId}/retry`, {});
  }

  rollbackDeployment(deploymentId: number): Observable<DeploymentRecord> {
    return this.http.post<DeploymentRecord>(`${this.baseUrl}/deployments/${deploymentId}/rollback`, {});
  }

  getMetrics(modelId: number): Observable<MetricRecord[]> {
    return this.http.get<MetricRecord[]>(`${this.baseUrl}/models/${modelId}/metrics`);
  }
}

export function describeApiError(error: unknown): string {
  const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg ?? 'Invalid request').join(', ');
  if (error instanceof Error && error.message) return error.message;
  return 'The API request failed. Check the backend connection and try again.';
}