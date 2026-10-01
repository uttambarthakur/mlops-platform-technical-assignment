import { Routes } from '@angular/router';
import { Layout } from './features/layout/layout';
import { RegisterModel } from './features/register-model/register-model';
import { ModelList } from './features/model-list/model-list';
import { DeploymentList } from './features/deployment-list/deployment-list';
import { ModelDetails } from './features/model-details/model-details';
import { RegisterDeployment } from './features/register-deployment/register-deployment';
import { Metrics } from './features/metrics/metrics';

export const routes: Routes = [
  {
    path: '',
    component: Layout,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'models/list' },
      { path: 'models/register', component: RegisterModel },
      { path: 'models/list', component: ModelList },
      { path: 'models/:model_id', component: ModelDetails },
      { path: 'deployment/register', component: RegisterDeployment},
      { path: 'deployments/list', component: DeploymentList },
      { path: 'metrics', component: Metrics },
    ]
  },
  { path: '**', redirectTo: 'models/list' }
];