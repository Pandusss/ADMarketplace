import { useNavigate } from 'react-router-dom';
import { Home, Handshake, Radio, Wallet, User } from 'lucide-react';
import styles from './BottomBar.module.scss';

export type BottomTab = 'profile' | 'deals' | 'feed' | 'channels' | 'wallet';

interface BottomBarProps {
    activeTab: BottomTab;
}

export function BottomBar({ activeTab }: BottomBarProps) {
    const navigate = useNavigate();

    // Navigation items mapping
    // Note: we use "Feed" as home, but keep key names consistent with existing code
    const items = [
        { key: 'profile' as const, label: 'Profile', icon: User, path: '/profile' },
        { key: 'wallet' as const, label: 'Wallet', icon: Wallet, path: '/wallet' },
        { key: 'feed' as const, label: 'Feed', icon: Home, path: '/feed' },
        { key: 'deals' as const, label: 'Deals', icon: Handshake, path: '/deals' },
        { key: 'channels' as const, label: 'Assets', icon: Radio, path: '/assets' },
    ];

    return (
        <nav className={styles.bar}>
            <div className={styles.container}>
                {items.map((item) => {
                    const isActive = activeTab === item.key;
                    const Icon = item.icon;

                    return (
                        <button
                            key={item.key}
                            onClick={() => navigate(item.path)}
                            className={`${styles.item} ${isActive ? styles.active : ''}`}
                        >
                            <Icon className={styles.icon} strokeWidth={isActive ? 2.5 : 2} />
                            <span className={styles.label}>{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
}
