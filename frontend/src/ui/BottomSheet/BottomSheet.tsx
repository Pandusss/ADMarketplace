import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import styles from './BottomSheet.module.scss';

interface BottomSheetProps {
    isOpen: boolean;
    onClose: () => void;
    title?: React.ReactNode;
    children: React.ReactNode;
}

export function BottomSheet({ isOpen, onClose, title, children }: BottomSheetProps) {
    const [visible, setVisible] = useState(false);
    const [animating, setAnimating] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setVisible(true);
            // Double rAF ensures the browser discovers the element in the DOM (hidden) 
            // before we apply the visible class to trigger the transition.
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    setAnimating(true);
                });
            });
        } else {
            setAnimating(false);
            const timer = setTimeout(() => setVisible(false), 300); // match transition duration
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    if (!visible) return null;

    return createPortal(
        <div className={`${styles.overlay} ${animating ? styles.visible : ''}`} onMouseDown={(e) => e.stopPropagation()} onTouchStart={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onClose(); }}>
            <div
                className={`${styles.sheet} ${animating ? styles.slideUp : ''}`}
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <div className={styles.handleWrapper}>
                    <div className={styles.handle} />
                </div>
                {title && (
                    <div className={styles.header}>
                        {typeof title === 'string' ? <h2 className={styles.title}>{title}</h2> : title}
                    </div>
                )}
                <div className={styles.content}>
                    {children}
                </div>
            </div>
        </div>,
        document.body
    );
}
