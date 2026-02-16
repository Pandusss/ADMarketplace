import React from 'react';
import styles from './AlertModal.module.scss';

interface AlertModalProps {
  isOpen: boolean;
  title?: string;
  message: string;
  buttonText?: string;
  onClose: () => void;
  onButtonClick?: () => void;
  secondaryButtonText?: string;
  onSecondaryButtonClick?: () => void;
}

export const AlertModal: React.FC<AlertModalProps> = ({
  isOpen,
  title,
  message,
  buttonText = 'OK',
  onClose,
  onButtonClick,
  secondaryButtonText,
  onSecondaryButtonClick,
}) => {
  if (!isOpen) return null;

  const handlePrimaryClick = () => {
    if (onButtonClick) {
      onButtonClick();
    } else {
      onClose();
    }
  };

  return (
    <div className={styles.modal} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className={styles.modalHeader}>
            <h3>{title}</h3>
            <button className={styles.modalClose} onClick={onClose}>✕</button>
          </div>
        )}
        <div className={styles.modalBody}>
          <p className={styles.message}>{message}</p>
          <div className={styles.buttonContainer}>
            {secondaryButtonText && onSecondaryButtonClick ? (
              <div style={{ display: 'flex', gap: 8, width: '100%' }}>
                <button
                  className={styles.button}
                  onClick={onSecondaryButtonClick}
                  style={{ flex: 1 }}
                >
                  {secondaryButtonText}
                </button>
                <button
                  className={styles.button}
                  onClick={handlePrimaryClick}
                  style={{ flex: 1 }}
                >
                  {buttonText}
                </button>
              </div>
            ) : (
              <button
                className={styles.button}
                onClick={handlePrimaryClick}
              >
                {buttonText}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
