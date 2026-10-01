import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { DeploymentList } from './deployment-list';

describe('DeploymentList', () => {
  let component: DeploymentList;
  let fixture: ComponentFixture<DeploymentList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeploymentList],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(DeploymentList);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
