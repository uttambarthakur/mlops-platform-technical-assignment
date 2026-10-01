import { DatePipe, isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiClient, DeploymentRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-deployment-list',
  imports: [DatePipe, RouterLink],
  templateUrl: './deployment-list.html',
  styleUrl: './deployment-list.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DeploymentList {
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly deployments = signal<DeploymentRecord[]>([]);
  protected readonly loading = signal(true);
  protected readonly pendingId = signal<number | null>(null);
  protected readonly errorMessage = signal('');
  protected readonly actionMessage = signal('');

  constructor() {
    if (isPlatformBrowser(this.platformId)) this.loadDeployments();
  }

  protected loadDeployments(): void {
    this.loading.set(true);
    this.errorMessage.set('');
    this.api.getDeployments().subscribe({
      next: (deployments) => this.deployments.set(deployments),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.loading.set(false);
      },
      complete: () => this.loading.set(false),
    });
  }

  protected countStatus(status: string): number {
    return this.deployments().filter((deployment) => deployment.status === status).length;
  }

  protected runAction(action: 'retry' | 'rollback', deploymentId: number): void {
    this.pendingId.set(deploymentId);
    this.actionMessage.set('');
    this.errorMessage.set('');
    const request = action === 'retry'
      ? this.api.retryDeployment(deploymentId)
      : this.api.rollbackDeployment(deploymentId);
    request.subscribe({
      next: (deployment) => {
        this.actionMessage.set(`Deployment ${deployment.id} is now ${deployment.status}.`);
        this.loadDeployments();
      },
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.pendingId.set(null);
      },
      complete: () => this.pendingId.set(null),
    });
  }
}
