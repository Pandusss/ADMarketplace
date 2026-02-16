import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { TonConnectUIProvider } from '@tonconnect/ui-react';
import App from './App';
import './styles/index.scss';

const manifestUrl = `${window.location.origin}/tonconnect-manifest.json`;

ReactDOM.createRoot(document.getElementById('root')!).render(
    <TonConnectUIProvider
      manifestUrl={manifestUrl}
      actionsConfiguration={{ twaReturnUrl: 'https://t.me/AdMarketplaceBot' }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </TonConnectUIProvider>
);
