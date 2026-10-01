import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiClient, ModelRecord, describeApiError } from '../api-client';

@Component({
  selector: 'app-register-model',
  imports: [RouterLink],
  templateUrl: './register-model.html',
  styleUrl: './register-model.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterModel {
  private readonly api = inject(ApiClient);
  protected readonly saving = signal(false);
  protected readonly errorMessage = signal('');
  protected readonly createdModel = signal<ModelRecord | null>(null);

  protected save(event: SubmitEvent): void {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const values = new FormData(form);
    this.saving.set(true);
    this.errorMessage.set('');
    this.createdModel.set(null);
    this.api.createModel({
      name: String(values.get('name') ?? '').trim(),
      framework: String(values.get('framework') ?? ''),
      algorithm: String(values.get('algorithm') ?? '').trim(),
      tags: String(values.get('tags') ?? '').split(',').map((tag) => tag.trim()).filter(Boolean),
    }).subscribe({
      next: (model) => this.createdModel.set(model),
      error: (error: unknown) => {
        this.errorMessage.set(describeApiError(error));
        this.saving.set(false);
      },
      complete: () => this.saving.set(false),
    });
  }
}
