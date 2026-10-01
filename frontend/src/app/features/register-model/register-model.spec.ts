import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RegisterModel } from './register-model';

describe('RegisterModel', () => {
  let component: RegisterModel;
  let fixture: ComponentFixture<RegisterModel>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterModel],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterModel);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
