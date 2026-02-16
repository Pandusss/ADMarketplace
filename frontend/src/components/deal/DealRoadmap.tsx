import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Text } from '../../ui';
import styles from './DealRoadmap.module.scss';

export type RoadmapStep = {
  id: number;
  title: string;
  desc?: string;
  right?: ReactNode;
  action?: { label: string; onClick: () => void };
  type?: 'default' | 'error';
};

export function DealRoadmap({
  steps,
  currentStep,
  completedUntilStep,
  initialShowFuture = false,
}: {
  steps: RoadmapStep[];
  currentStep: number;
  completedUntilStep?: number;
  initialShowFuture?: boolean;
}) {
  const [showFuture, setShowFuture] = useState(initialShowFuture);

  const { completedSteps, activeStep, futureSteps } = useMemo(() => {
    const active = steps.find((s) => s.id === currentStep) ?? null;
    const completed = completedUntilStep != null
      ? steps.filter((s) => s.id <= completedUntilStep && s.id !== currentStep)
      : steps.filter((s) => s.id < currentStep && s.id !== currentStep);
    const future = steps.filter((s) => s.id > currentStep);
    return { completedSteps: completed, activeStep: active, futureSteps: future };
  }, [steps, currentStep, completedUntilStep]);

  return (
    <div className={styles.stepper} aria-label="Deal roadmap">
      {/* Completed */}
      {completedSteps.map((step) => (
        <div key={step.id} className={styles.step}>
          <div className={styles.stepConnector} />
          <div className={styles.stepContent}>
            <div className={styles.markerWrapper}>
              <div className={`${styles.marker} ${step.type === 'error' ? styles.error : styles.completed}`}>
                {step.type === 'error' ? <span className={styles.checkmark}>✕</span> : <span className={styles.checkmark}>✓</span>}
              </div>
            </div>
            <div className={styles.stepText}>
              <div className={styles.stepItem}>
                <Text type="text">{step.title}</Text>
                {step.right ?? (step.action ? (
                  <button className={styles.txBtn} type="button" onClick={step.action.onClick}>
                    {step.action.label}
                  </button>
                ) : null)}
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* Active */}
      {activeStep && (
        <div className={styles.step}>
          <div
            className={`${styles.stepConnector} ${futureSteps.length > 0 ? (showFuture ? styles.connectorFadeToToggle : styles.connectorFade) : ''
              }`}
          />
          <div className={styles.stepContent}>
            <div className={styles.markerWrapper}>
              <div className={`${styles.marker} ${activeStep.type === 'error' ? styles.error : styles.active}`}>
                {activeStep.type === 'error' ? (
                  <span className={styles.checkmark}>✕</span>
                ) : (
                  <>
                    <div className={styles.activePulse} />
                    <div className={styles.activeRipple} />
                  </>
                )}
              </div>
            </div>
            <div className={styles.stepText}>
              <div className={`${styles.stepItem} ${styles.activeStepItem}`}>
                <div style={{ minWidth: 0 }}>
                  <Text type="text" weight="bold">
                    {activeStep.title}
                  </Text>
                  {activeStep.desc ? (
                    <Text type="caption" color="secondary" style={{ display: 'block', marginTop: 4 }}>
                      {activeStep.desc}
                    </Text>
                  ) : null}
                </div>
                {activeStep.right ?? (activeStep.action ? (
                  <button className={styles.txBtn} type="button" onClick={activeStep.action.onClick}>
                    {activeStep.action.label}
                  </button>
                ) : null)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Future */}
      {futureSteps.length > 0 && (
        <>
          <div className={`${styles.toggleStep} ${showFuture ? styles.toggleStepExpanded : ''}`}>
            <button className={styles.futureToggle} onClick={() => setShowFuture((v) => !v)} type="button">
              <div className={`${styles.toggleIcon} ${showFuture ? styles.rotated : ''}`}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </div>
              <Text type="caption" color="secondary">
                Next steps ({futureSteps.length})
              </Text>
            </button>
            <div className={styles.toggleConnector} />
          </div>

          <div className={`${styles.futureSteps} ${showFuture ? styles.futureStepsVisible : ''}`}>
            {futureSteps.map((step, index) => (
              <div key={step.id} className={styles.step}>
                <div className={`${styles.stepConnector} ${index === futureSteps.length - 1 ? styles.connectorLast : ''}`} />
                <div className={styles.stepContent}>
                  <div className={styles.markerWrapper}>
                    <div className={`${styles.marker} ${styles.pending}`} />
                  </div>
                  <div className={styles.stepText}>
                    <div className={styles.stepItem}>
                      <div style={{ minWidth: 0 }}>
                        <Text type="text" color="secondary">
                          {step.title}
                        </Text>
                        {step.desc ? (
                          <Text type="caption" color="secondary" style={{ display: 'block', marginTop: 4 }}>
                            {step.desc}
                          </Text>
                        ) : null}
                      </div>
                      {step.right ?? (step.action ? (
                        <button className={styles.txBtn} type="button" onClick={step.action.onClick}>
                          {step.action.label}
                        </button>
                      ) : null)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

