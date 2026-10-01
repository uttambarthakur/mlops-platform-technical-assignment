import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ModelDetails } from './model-details';

describe('ModelDetails', () => {
  let component: ModelDetails;
  let fixture: ComponentFixture<ModelDetails>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ModelDetails],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(ModelDetails);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
