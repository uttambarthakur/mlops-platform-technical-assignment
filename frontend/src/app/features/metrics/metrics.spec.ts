import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Metrics } from './metrics';

describe('Metrics', () => {
  let component: Metrics;
  let fixture: ComponentFixture<Metrics>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Metrics],
    }).compileComponents();

    fixture = TestBed.createComponent(Metrics);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
