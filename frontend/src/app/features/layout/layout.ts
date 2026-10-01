import { isPlatformBrowser } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ApiClient } from '../api-client';


@Component({
  selector: 'app-layout',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './layout.html',
  styleUrl: './layout.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Layout {
  private readonly api = inject(ApiClient);
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly apiStatus = signal('Checking API');
  protected readonly tokenInput = signal('');
  protected readonly tokenMessage = signal('');

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.api.getHealth().subscribe({
        next: () => this.apiStatus.set('API connected'),
        error: () => this.apiStatus.set('API unavailable'),
      });
    }
  }

  protected updateToken(event: Event): void {
    this.tokenInput.set((event.target as HTMLInputElement).value);
  }

  protected saveToken(event: SubmitEvent): void {
    event.preventDefault();
    this.api.setAccessToken(this.tokenInput());
    this.tokenInput.set('');
    this.tokenMessage.set(this.api.hasAccessToken() ? 'Token saved for this browser session.' : 'Token cleared.');
  }

  protected clearToken(): void {
    this.api.setAccessToken('');
    this.tokenInput.set('');
    this.tokenMessage.set('Token cleared.');
  }
}
