import styles from './BottomNav.module.scss';
import { useNavigate } from 'react-router-dom';

export type BottomTab = 'profile' | 'deals' | 'feed' | 'channels' | 'wallet';

export function BottomNav({
  activeTab,
}: {
  activeTab: BottomTab;
}) {
  // UX rule: fixed global navigation with 5 tabs.
  // Profile / Deals / Feed (main) / My Assets / Wallet.
  const navigate = useNavigate();
  return (
    <div className={styles.wrap} aria-label="Bottom navigation">
      <nav className={styles.nav}>
        <button
          className={`${styles.item} ${activeTab === 'profile' ? styles.active : ''}`}
          aria-current={activeTab === 'profile' ? 'page' : undefined}
          onClick={() => navigate('/profile')}
        >
          <span className={styles.dot} aria-hidden />
          <span>Profile</span>
        </button>

        <button
          className={`${styles.item} ${activeTab === 'deals' ? styles.active : ''}`}
          aria-current={activeTab === 'deals' ? 'page' : undefined}
          onClick={() => navigate('/deals')}
        >
          <span className={styles.dot} aria-hidden />
          <span>Deals</span>
        </button>

        <button
          className={`${styles.item} ${styles.main} ${activeTab === 'feed' ? styles.active : ''}`}
          aria-current={activeTab === 'feed' ? 'page' : undefined}
          onClick={() => navigate('/feed')}
        >
          <span className={styles.dot} aria-hidden />
          <span>FEED</span>
        </button>

        <button
          className={`${styles.item} ${activeTab === 'channels' ? styles.active : ''}`}
          aria-current={activeTab === 'channels' ? 'page' : undefined}
          onClick={() => navigate('/assets/channels')}
        >
          <span className={styles.dot} aria-hidden />
          <span>My Assets</span>
        </button>

        <button
          className={`${styles.item} ${activeTab === 'wallet' ? styles.active : ''}`}
          aria-current={activeTab === 'wallet' ? 'page' : undefined}
          onClick={() => navigate('/wallet')}
        >
          <span className={styles.dot} aria-hidden />
          <span>Wallet</span>
        </button>
      </nav>
    </div>
  );
}

