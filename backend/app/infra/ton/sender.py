"""
TON transaction sender module (Subwallets)
Refactored to be Async-First and use httpx.
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, TypedDict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from tonutils.client import ToncenterV3Client
    from tonutils.wallet import WalletV4R2
    TONUTILS_AVAILABLE = True
except ImportError:
    TONUTILS_AVAILABLE = False
    logger.warning("tonutils is not installed. Install with: pip install tonutils")


class TonResult(TypedDict):
    success: bool
    tx_hash: Optional[str]
    error: Optional[str]
    amount: Optional[str]
    from_address: Optional[str]
    details: Optional[Dict[str, Any]]

class TONSender:
    """
    TON transaction sender class with subwallets support.
    Async-first implementation.
    """
    
    def __init__(self):
        self.mnemonic = settings.ton_mnemonic
        self.network = settings.ton_network
        self.api_key = settings.ton_api_key
        self.client: Optional[httpx.AsyncClient] = None
        
        if not TONUTILS_AVAILABLE:
            logger.error("tonutils library is not available")
            return
        
        if not self.mnemonic:
            logger.warning("GUARANTOR_MNEMONIC is not configured")
            return
        
        logger.info(f"TON Sender initialized (network: {self.network})")

    async def start(self):
        """Initialize persistent HTTP client."""
        if not self.client:
            self.client = httpx.AsyncClient(timeout=10.0)
            logger.info("TON Sender HTTP client started")

    async def stop(self):
        """Close persistent HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("TON Sender HTTP client closed")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=10.0)
        return self.client

    async def _get_balance(self, address: str) -> float:
        """Get wallet balance asynchronously via tonapi.io"""
        url = f"https://tonapi.io/v2/accounts/{address}"
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            
        try:
            client = await self._get_http_client()
            response = await client.get(url, headers=headers)
                
            if response.status_code == 200:
                data = response.json()
                return int(data.get('balance', 0)) / 1_000_000_000
            else:
                logger.warning(f"Failed to get balance for {address}: {response.status_code}")
                return 0.0
        except Exception as e:
            logger.error(f"Error fetching balance for {address}: {e}")
            return 0.0
    
    async def _check_wallet_deployed(self, address: str) -> bool:
        """Check if wallet is deployed using tonapi.io"""
        url = f"https://tonapi.io/v2/accounts/{address}"
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            
        try:
            client = await self._get_http_client()
            response = await client.get(url, headers=headers)
                
            if response.status_code == 200:
                return response.json().get('status') == 'active'
            return False
        except Exception as e:
            logger.error(f"Error checking wallet status for {address}: {e}")
            return False
    
    async def _create_wallet_and_client(self, subwallet_id: int):
        """
        Create ToncenterV3Client and wallet instance.
        """
        try:
            # ToncenterV3Client creates its own aiohttp session, so we can't easily reuse our httpx client here.
            # That's fine for now as it's used for the wallet interaction itself.
            client = ToncenterV3Client(is_testnet=(self.network == 'testnet'))
            wallet_data = WalletV4R2.from_mnemonic(client, self.mnemonic.strip().split(), subwallet_id)
            
            if isinstance(wallet_data, tuple):
                wallet = wallet_data[0]
            else:
                wallet = wallet_data
            
            return client, wallet
        except Exception as e:
            logger.error(f"Error creating wallet for subwallet_id={subwallet_id}: {e}", exc_info=True)
            return None, None
    
    async def _ensure_wallet_deployed(self, wallet, wallet_address: str) -> bool:
        """Ensure wallet is deployed, deploy if necessary"""
        is_deployed = await self._check_wallet_deployed(wallet_address)
        if is_deployed:
            return True

        logger.info(f"Deploying wallet {wallet_address}...")
        try:
            await wallet.deploy()
            # Wait for deployment
            for i in range(15):
                await asyncio.sleep(2)
                if await self._check_wallet_deployed(wallet_address):
                    logger.info(f"Wallet {wallet_address} deployed successfully.")
                    return True
            logger.warning(f"Wallet {wallet_address} deploy timed out.")
            return False
        except Exception as e:
            logger.error(f"Failed to deploy wallet {wallet_address}: {e}")
            return False
    
    async def deploy_subwallet(self, subwallet_id: int, payment_address: str) -> TonResult:
        """Deploy subwallet asynchronously"""
        if not TONUTILS_AVAILABLE:
            return {'success': False, 'error': 'tonutils not installed', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
        
        client = None
        try:
            # Check if target 'payment_address' is deployed? 
            if await self._check_wallet_deployed(payment_address):
                return {'success': True, 'details': {'already_deployed': True}, 'tx_hash': None, 'error': None, 'amount': None, 'from_address': None}
            
            client, wallet = await self._create_wallet_and_client(subwallet_id)
            if not client or not wallet:
                return {'success': False, 'error': 'Failed to create wallet instance', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
            
            # Check guarantor balance
            balance = await self._get_balance(wallet.address.to_str())
            if balance < 0.05:
                return {'success': False, 'error': f'Insufficient funds: {balance} TON', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
            
            deploy_success = await self._ensure_wallet_deployed(wallet, wallet.address.to_str())
            
            if deploy_success:
                return {'success': True, 'from_address': wallet.address.to_str(), 'details': {'subwallet_id': subwallet_id}, 'tx_hash': None, 'error': None, 'amount': None}
            else:
                return {'success': False, 'error': 'Deploy timeout or failed', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}

        except Exception as e:
            logger.exception(f"Deploy failed: {e}")
            return {'success': False, 'error': str(e), 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
        finally:
            if client and hasattr(client, "close"):
                await client.close()
    
    async def send_ton(
        self, 
        subwallet_id: int, 
        destination: str, 
        amount: Decimal, 
        comment: str = "", 
        send_mode: int = 3
    ) -> TonResult:
        """Send TON from specific subwallet (asynchronously)"""
        if not TONUTILS_AVAILABLE:
            return {'success': False, 'error': 'tonutils not installed', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
        
        client = None
        try:
            client, wallet = await self._create_wallet_and_client(subwallet_id)
            if not client or not wallet:
                return {'success': False, 'error': 'Failed to create wallet instance', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
            
            wallet_address = wallet.address.to_str()
            
            # Determine send amount
            if send_mode == 128:
                send_amount = 0.0
                amount_log = "ALL"
            else:
                balance = await self._get_balance(wallet_address)
                network_fee = 0.01 # estimated
                amount_float = float(amount)
                
                if balance < network_fee:
                    return {'success': False, 'error': 'Insufficient funds for fee', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
                
                send_amount = min(amount_float, balance) - network_fee
                if send_amount <= 0:
                    return {'success': False, 'error': 'Insufficient funds', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
                amount_log = str(send_amount)
            
            if not await self._ensure_wallet_deployed(wallet, wallet_address):
                return {'success': False, 'error': 'Failed to deploy wallet', 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
            
            logger.info(f"Sending {amount_log} TON from {wallet_address} to {destination} (mode={send_mode})")
            
            tx_hash = await wallet.transfer(
                destination=destination, 
                amount=send_amount, 
                body=comment, 
                send_mode=send_mode
            )
            
            return {
                'success': True, 
                'tx_hash': tx_hash or 'unknown', 
                'amount': amount_log,
                'from_address': wallet_address,
                'error': None,
                'details': None
            }
        except Exception as e:
            logger.exception(f"Transfer failed: {e}")
            return {'success': False, 'error': str(e), 'tx_hash': None, 'amount': None, 'from_address': None, 'details': None}
        finally:
            if client and hasattr(client, "close"):
                await client.close()

# Global sender instance
ton_sender = TONSender()
