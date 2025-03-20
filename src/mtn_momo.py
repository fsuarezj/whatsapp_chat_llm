import requests
from typing import Dict, List, Optional
from datetime import datetime
import json
from loguru import logger

class MTNMoMo:
    def __init__(self, api_key: str, user_id: str, primary_key: str, environment: str = 'sandbox'):
        """
        Initialize MTN MoMo Client
        
        Args:
            api_key: Your MTN MoMo API Key
            user_id: Your MTN MoMo User ID
            primary_key: Your MTN MoMo Primary Key
            environment: Environment to use ('sandbox' or 'production')
        """
        self.api_key = api_key
        self.user_id = user_id
        self.primary_key = primary_key
        self.environment = environment
        
        # Set base URL based on environment
        self.base_url = "https://sandbox.momodeveloper.mtn.com" if environment == 'sandbox' else "https://momodeveloper.mtn.com"

    def _get_headers(self) -> Dict:
        """Get headers for API requests"""
        return {
            'X-Reference-Id': self.user_id,
            'X-Target-Environment': self.environment,
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Content-Type': 'application/json'
        }

    def check_transaction(self, transaction_id: str) -> Dict:
        """
        Check transaction details by ID
        
        Args:
            transaction_id: The transaction ID to check
            
        Returns:
            Dict containing transaction details (date, amount, phone number)
        """
        try:
            endpoint = f"{self.base_url}/collection/v1_0/transaction/{transaction_id}"
            
            response = requests.get(
                endpoint,
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Transaction {transaction_id} checked successfully")
            
            return {
                'date': data.get('date'),
                'amount': data.get('amount'),
                'phone_number': data.get('payer', {}).get('partyId')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check transaction {transaction_id}: {str(e)}")
            raise

    def get_last_transactions(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """
        Get last transactions for a phone number
        
        Args:
            phone_number: The phone number to check
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction details (date, amount, transaction_id)
        """
        try:
            endpoint = f"{self.base_url}/collection/v1_0/accountholder/{phone_number}/transactions"
            
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                params={'limit': limit}
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Last transactions for {phone_number} retrieved successfully")
            
            return [{
                'date': transaction.get('date'),
                'amount': transaction.get('amount'),
                'transaction_id': transaction.get('transactionId')
            } for transaction in data.get('transactions', [])]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get last transactions for {phone_number}: {str(e)}")
            raise

    def request_payment(self, phone_number: str, amount: float, 
                       currency: str = 'EUR', message: Optional[str] = None) -> Dict:
        """
        Request a payment from a phone number
        
        Args:
            phone_number: The phone number to request payment from
            amount: The amount to request
            currency: The currency code (default: EUR)
            message: Optional message to include with the request
            
        Returns:
            Dict containing the payment request details
        """
        try:
            endpoint = f"{self.base_url}/collection/v1_0/requesttopay"
            
            payload = {
                "amount": str(amount),
                "currency": currency,
                "externalId": f"REQ{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": message or "Payment request",
                "payeeNote": "Payment request",
                "callbackUrl": "https://your-callback-url.com/webhook",  # Replace with your webhook URL
                "status": "PENDING"
            }
            
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Payment request sent to {phone_number} successfully")
            
            return {
                'status': data.get('status'),
                'transaction_id': data.get('transactionId'),
                'amount': amount,
                'phone_number': phone_number
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to request payment from {phone_number}: {str(e)}")
            raise 