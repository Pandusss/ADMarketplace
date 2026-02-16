import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { FeedPage } from './pages/FeedPage/FeedPage';
import { DealsPage } from './pages/DealsPage/DealsPage';
import { DealDetailsPage } from './pages/DealDetailsPage/DealDetailsPage';
import { CampaignOfferDetailsPage } from './pages/CampaignOfferDetailsPage/CampaignOfferDetailsPage';
import { ChannelOfferDetailsPage } from './pages/ChannelOfferDetailsPage/ChannelOfferDetailsPage';
import { BottomBar, BottomTab } from './ui';
import { MyChannelsPage } from './pages/MyChannelsPage/MyChannelsPage';
import { ChannelDetailsPage } from './pages/ChannelDetailsPage/ChannelDetailsPage';
import { StartDealPage } from './pages/StartDealPage/StartDealPage';
import { ProfilePage } from './pages/ProfilePage/ProfilePage';
import { PostTemplatesPage } from './pages/PostTemplatesPage/PostTemplatesPage';
import { WalletPage } from './pages/WalletPage/WalletPage';
import { MyAssetsPage } from './pages/MyAssetsPage/MyAssetsPage';
import { CreateCampaignPage } from './pages/CreateCampaignPage/CreateCampaignPage';
import { CampaignDetailsPage } from './pages/CampaignDetailsPage/CampaignDetailsPage';
import { useEffect } from 'react';

import { AnimatePresence } from 'framer-motion';
import { PageTransition } from './components/PageTransition/PageTransition';

export default function App() {
  // ... (keep useEffect)
  useEffect(() => {
    // Telegram WebApp bootstrap
    const tg = (window as any).Telegram?.WebApp;
    try {
      tg?.ready?.();
      tg?.expand?.();

      // Theme handling
      const applyTheme = () => {
        const scheme = tg?.colorScheme || 'light';
        document.documentElement.setAttribute('data-theme', scheme);

        // Optional: Update header color if needed
        if (scheme === 'dark') {
          tg?.setHeaderColor?.('#1C1C1E'); // Matches our secondary bg
          tg?.setBackgroundColor?.('#1C1C1E');
        } else {
          tg?.setHeaderColor?.('#ffffff');
          tg?.setBackgroundColor?.('#ffffff');
        }
      };

      applyTheme();

      // Listen for theme changes if Telegram supports it (or just rely on init)
      tg?.onEvent?.('themeChanged', applyTheme);

      return () => {
        tg?.offEvent?.('themeChanged', applyTheme);
      };

    } catch (e) {
      console.error('Telegram WebApp init failed', e);
      // Fallback for local dev
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, []);

  return (
    <AppFrame />
  );
}

function AppFrame() {
  const location = useLocation();
  const activeTab: BottomTab = location.pathname.startsWith('/profile')
    ? 'profile'
    : location.pathname.startsWith('/deals') || location.pathname.startsWith('/campaign-offers') || location.pathname.startsWith('/channel-offers') || location.pathname.startsWith('/offers')
      ? 'deals'
      : location.pathname.startsWith('/my-channels') || location.pathname.startsWith('/assets')
        ? 'channels'
        : location.pathname.startsWith('/wallet')
          ? 'wallet'
          : 'feed';

  return (
    <>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Navigate to="/feed" replace />} />
          <Route path="/feed" element={<PageTransition><FeedPage /></PageTransition>} />
          <Route path="/feed/buy/new" element={<PageTransition><CreateCampaignPage /></PageTransition>} />
          <Route path="/feed/buy/:campaignId" element={<PageTransition><CampaignDetailsPage /></PageTransition>} />
          <Route path="/channels/:channelId" element={<PageTransition><ChannelDetailsPage /></PageTransition>} />
          <Route path="/start-deal/:channelId" element={<PageTransition><StartDealPage /></PageTransition>} />
          <Route path="/deals" element={<PageTransition><DealsPage /></PageTransition>} />
          <Route path="/deals/:dealId" element={<PageTransition><DealDetailsPage /></PageTransition>} />
          <Route path="/campaign-offers/:offerId" element={<PageTransition><CampaignOfferDetailsPage /></PageTransition>} />
          <Route path="/offers/:offerId" element={<PageTransition><CampaignOfferDetailsPage /></PageTransition>} />
          <Route path="/channel-offers/:offerId" element={<PageTransition><ChannelOfferDetailsPage /></PageTransition>} />
          <Route path="/my-channels" element={<Navigate to="/assets" replace />} />
          <Route path="/profile" element={<PageTransition><ProfilePage /></PageTransition>} />
          <Route path="/profile/templates" element={<Navigate to="/assets" replace />} />
          <Route path="/assets" element={<PageTransition><MyAssetsPage /></PageTransition>} />
          <Route path="/wallet" element={<PageTransition><WalletPage /></PageTransition>} />
        </Routes>
      </AnimatePresence>

      <BottomBar activeTab={activeTab} />
    </>
  );
}
