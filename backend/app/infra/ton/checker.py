"""
TON payment checker module (Subwallets)
Async implementation using httpx.
"""
import base64
import asyncio
import logging
from typing import Optional, Dict, List, Any

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class TONChecker:
    """
    Checker for payment verification via subwallets system.
    Async-first implementation.
    """
    
    def __init__(self):
        self.api_url = settings.ton_api_url
        self.api_key = settings.ton_api_key
        self.headers = {}
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
        
        logger.info("TON Checker initialized (Async)")
    
    @staticmethod
    def _decode_tx_hash(tx_hash: str) -> str:
        """Decode base64 transaction hash to hex if needed"""
        if tx_hash and len(tx_hash) > 64:
            try:
                return base64.b64decode(tx_hash).hex()
            except Exception:
                return tx_hash
        return tx_hash
    
    async def get_balance_async(self, address: str) -> float:
        """
        Get balance for specific address (NATIVE TON ONLY)
        """
        try:
            url = f"{self.api_url}/accounts/{address}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                balance_nanoton = int(data.get('balance', 0))
                return balance_nanoton / 1_000_000_000
            else:
                logger.error(f"Failed to get balance for {address}: HTTP {response.status_code}")
                return 0.0
        except Exception as e:
            logger.error(f"Failed to get balance for {address[:20]}...: {e}")
            return 0.0

    def get_balance(self, address: str) -> float:
        """Sync wrapper for legacy code"""
        try:
           return asyncio.run(self.get_balance_async(address))
        except Exception as e:
            logger.error(f"Sync balance check failed: {e}")
            return 0.0
    
    async def _get_transaction_count_async(self, address: str) -> int:
        """
        Get count of INCOMING transactions for address
        """
        try:
            url = f"{self.api_url}/blockchain/accounts/{address}/transactions"
            params = {'limit': 100}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                transactions = data.get('transactions', [])
                incoming_count = 0
                for tx in transactions:
                    in_msg = tx.get('in_msg')
                    if in_msg and in_msg.get('value', 0) > 0:
                        incoming_count += 1
                return incoming_count
            return 0
        except Exception:
            return 0
    
    async def _get_last_incoming_tx_hash_async(self, address: str) -> Optional[str]:
        """
        Get hash of last incoming transaction for address
        """
        try:
            url = f"{self.api_url}/blockchain/accounts/{address}/transactions"
            params = {'limit': 10}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                transactions = data.get('transactions', [])
                
                if not transactions:
                    transactions = data.get('events', []) or data.get('result', [])
                
                for tx in transactions:
                    in_msg = tx.get('in_msg')
                    if in_msg and int(in_msg.get('value', 0)) > 0:
                        tx_hash = tx.get('hash') or (tx.get('transaction_id', {}).get('hash') if isinstance(tx.get('transaction_id'), dict) else None)
                        return self._decode_tx_hash(tx_hash)
                return None
            return None
        except Exception:
            return None

    def _get_last_incoming_tx_hash(self, address: str) -> Optional[str]:
         """Sync wrapper"""
         try:
             return asyncio.run(self._get_last_incoming_tx_hash_async(address))
         except Exception:
             return None

    async def _get_last_transaction_async(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get last incoming transaction via toncenter.com (fallback)
        """
        try:
            # Note: toncenter requires API key usually, but v2/getTransactions works without freely for low usage
            url = "https://toncenter.com/api/v2/getTransactions"
            params = {'address': address, 'limit': 10}
            if self.api_key: # If we have key, try to use mainnet client if configured, otherwise direct request
                 pass 

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
            
            if response.status_code == 200:
                transactions = response.json().get('result', [])
                for tx in transactions:
                    in_msg = tx.get('in_msg', {})
                    if not in_msg or in_msg.get('source') == '': 
                        continue
                    
                    tx_id = tx.get('transaction_id', {})
                    tx_hash = self._decode_tx_hash(tx_id.get('hash', ''))
                        
                    return {
                        'hash': tx_hash,
                        'timestamp': tx.get('utime', 0),
                        'amount': int(in_msg.get('value', 0)) / 1_000_000_000,
                        'sender': in_msg.get('source')
                    }
            return None
        except Exception:
            return None
            
    def _get_last_transaction(self, address: str) -> Optional[Dict[str, Any]]:
        """Sync wrapper"""
        try:
            return asyncio.run(self._get_last_transaction_async(address))
        except Exception:
            return None


# Global checker instance
ton_checker = TONChecker()
