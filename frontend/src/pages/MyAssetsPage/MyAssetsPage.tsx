import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Text, BottomSheet } from '../../ui';
import { MyChannelsPage } from '../MyChannelsPage/MyChannelsPage';
import { PostTemplatesPage } from '../PostTemplatesPage/PostTemplatesPage';
import { AddChannelForm } from '../AddChannelPage/AddChannelForm';
import { CreateTemplateForm } from '../PostTemplatesPage/CreateTemplateForm';
import styles from './MyAssetsPage.module.scss';
import { Plus } from 'lucide-react';

type AssetsTab = 'channels' | 'templates';

export function MyAssetsPage() {
  const navigate = useNavigate();

  const [tab, setTab] = useState<AssetsTab>(() => {
    const raw = localStorage.getItem('assets_tab');
    if (raw === 'channels' || raw === 'templates') return raw;
    return 'channels';
  });
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Sync refresh trigger
  const [refreshChannels, setRefreshChannels] = useState(0);
  const [refreshTemplates, setRefreshTemplates] = useState(0);

  useEffect(() => {
    localStorage.setItem('assets_tab', tab);
  }, [tab]);

  const handleSuccess = () => {
    setIsAddModalOpen(false);
    // Trigger refresh of list
    if (tab === 'channels') setRefreshChannels(prev => prev + 1);
    else setRefreshTemplates(prev => prev + 1);
  };

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">My Assets</Text>
          <Button
            variant="primary"
            size="small"
            fullWidth={false}
            style={{ padding: 8 }}
            onClick={() => setIsAddModalOpen(true)}
          >
            <Plus size={20} />
          </Button>
        </div>

        <div className={styles.segmented} role="tablist" aria-label="My assets sections">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'channels'}
            className={`${styles.segmentedItem} ${tab === 'channels' ? styles.active : ''}`}
            onClick={() => setTab('channels')}
          >
            Channels
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'templates'}
            className={`${styles.segmentedItem} ${tab === 'templates' ? styles.active : ''}`}
            onClick={() => setTab('templates')}
          >
            Templates
          </button>
        </div>

        <div className={styles.body}>
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, x: tab === 'channels' ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: tab === 'channels' ? 10 : -10 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              {tab === 'channels' ? (
                <MyChannelsPage embedded key={refreshChannels} />
              ) : (
                <PostTemplatesPage embedded key={refreshTemplates} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <BottomSheet
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          title={tab === 'channels' ? 'Add Channel' : 'New Template'}
        >
          {tab === 'channels' ? (
            <AddChannelForm onSuccess={handleSuccess} />
          ) : (
            <CreateTemplateForm onSuccess={handleSuccess} onCancel={() => setIsAddModalOpen(false)} />
          )}
        </BottomSheet>
      </div>
    </div>
  );
}
