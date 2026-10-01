import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RegisterDeployment } from './register-deployment';

describe('RegisterDeployment', () => {
  let component: RegisterDeployment;
  let fixture: ComponentFixture<RegisterDeployment>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterDeployment],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterDeployment);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
