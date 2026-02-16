import { DEAL_STATUS_ORDER, getDealStatusIndex, prettyDealStatus } from '../../../domain/dealStatus';
import { DealStatus } from '../../../domain/types';
import { Button, Text } from '../../../ui';
import styles from './DealTimeline.module.scss';

export function DealTimeline({
  status,
  terminalFromStatus,
  paymentTxHash,
  escrowAddress,
  escrowNetwork,
  paymentConfirmedAt,
}: {
  status: DealStatus;
  terminalFromStatus?: DealStatus;
  paymentTxHash?: string | null;
  escrowAddress?: string | null;
  escrowNetwork?: string | null;
  paymentConfirmedAt?: string | null;
}) {
  const currentIdx = getDealStatusIndex(status);
  const terminalFromIdx = terminalFromStatus ? getDealStatusIndex(terminalFromStatus) : null;
  const isTerminal = status === 'cancelled' || status === 'refunded';
  // Show button if payment was confirmed (status is creative_draft or later, and payment_confirmed_at exists)
  const paymentWasConfirmed = paymentConfirmedAt && (status === 'creative_draft' || getDealStatusIndex(status) > getDealStatusIndex('pending_payment'));

  return (
    <div className={styles.timeline} aria-label="Deal status timeline">
      {DEAL_STATUS_ORDER.map((s, idx) => {
        // If deal is cancelled/refunded, only mark the steps as done up to where it was terminated.
        const isDone = isTerminal ? (terminalFromIdx !== null ? idx <= terminalFromIdx : false) : idx < currentIdx;
        const isCurrent = idx === currentIdx;
        const isFuture = idx > currentIdx;
        const isFundsHeld = s === 'funds_held';
        // Show button on "Funds Held" step if payment was confirmed
        const showTxButton = isFundsHeld && paymentWasConfirmed && (paymentTxHash || escrowAddress);
        
        return (
          <div key={s} className={`${styles.item} ${isFuture ? styles.future : ''}`}>
            <div className={`${styles.dot} ${isDone ? styles.done : ''} ${isCurrent ? styles.current : ''}`} />
            <div className={styles.label} style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'nowrap', width: '100%', minWidth: 0 }}>
                <Text type="text" weight={isCurrent ? 'bold' : 'normal'} style={{ whiteSpace: 'nowrap', flexShrink: 1, minWidth: 0 }}>
                {prettyDealStatus(s)}
              </Text>
                {showTxButton && (
                  <button
                    style={{ 
                      padding: '1px 4px', 
                      fontSize: '9px', 
                      height: '18px',
                      lineHeight: '16px',
                      flexShrink: 0,
                      whiteSpace: 'nowrap',
                      border: '1px solid var(--color-border-separator, #e0e0e0)',
                      borderRadius: '3px',
                      backgroundColor: 'transparent',
                      cursor: 'pointer',
                      color: 'var(--color-text-primary, #000)',
                      width: '26px',
                      minWidth: '26px',
                      maxWidth: '26px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: 'inherit',
                      boxSizing: 'border-box'
                    }}
                    onClick={() => {
                      const network = escrowNetwork || 'mainnet';
                      // If we have transaction hash, link directly to transaction, otherwise to address
                      let explorerUrl: string;
                      if (paymentTxHash) {
                        // Direct link to transaction
                        explorerUrl = network === 'testnet' 
                          ? `https://testnet.tonviewer.com/transaction/${paymentTxHash}`
                          : `https://tonviewer.com/transaction/${paymentTxHash}`;
                      } else if (escrowAddress) {
                        // Fallback to address page
                        explorerUrl = network === 'testnet' 
                          ? `https://testnet.tonviewer.com/${escrowAddress}`
                          : `https://tonviewer.com/${escrowAddress}`;
                      } else {
                        return;
                      }
                      window.open(explorerUrl, '_blank');
                    }}
                  >
                    TX
                  </button>
                )}
              </div>
              {isCurrent && (
                <Text type="caption" color="secondary">
                  Current step
                </Text>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

