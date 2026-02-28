"""Arke API Client for fetching sales orders and managing production"""

import os
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ArkeAPIClient:
    """Client for interacting with the Arke production management API"""

    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the Arke API client

        Args:
            base_url: Base URL for the Arke API (defaults to env variable)
            username: Username for authentication (defaults to env variable)
            password: Password for authentication (defaults to env variable)
        """
        self.base_url = base_url or os.getenv("ARKE_API_BASE_URL")
        self.username = username or os.getenv("ARKE_USERNAME")
        self.password = password or os.getenv("ARKE_PASSWORD")

        if not all([self.base_url, self.username, self.password]):
            raise ValueError("Missing required API configuration. Check your .env file.")

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.access_token = None
        self._login()

    def _login(self):
        """Authenticate with the Arke API and obtain access token"""
        url = f"{self.base_url}/login"
        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Try different possible token field names
            self.access_token = data.get("access_token") or data.get("token") or data.get("accessToken")

            if not self.access_token:
                raise ValueError(f"No access token received from login response")

            # Update session headers with bearer token
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })

        except requests.RequestException as e:
            print(f"Error during authentication: {e}")
            raise

    def get_sales_orders(self, status: str = "accepted") -> List[Dict[str, Any]]:
        """
        Fetch sales orders from the Arke API

        Args:
            status: Filter by order status (default: "accepted")

        Returns:
            List of sales order dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/sales/order"
        params = {"status": status}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching sales orders: {e}")
            raise

    def get_products(self) -> List[Dict[str, Any]]:
        """
        Fetch all products from the Arke API

        Returns:
            List of product dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/product/product"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching products: {e}")
            raise

    def find_product_by_extra_id(self, extra_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a product by its extra_id

        Args:
            extra_id: The product extra_id to search for

        Returns:
            Product dictionary or None if not found
        """
        # Try searching with filter parameter
        try:
            url = f"{self.base_url}/product"
            params = {"extra_id": extra_id}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            products = response.json()
            if products and len(products) > 0:
                return products[0]
        except:
            pass

        return None

    def get_sales_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific sales order

        Args:
            order_id: ID of the sales order

        Returns:
            Sales order details including line items (products and quantities)

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/sales/order/{order_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching order details for {order_id}: {e}")
            raise

    def create_production_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a production order in the Arke system

        Args:
            order_data: Production order details (product, quantity, dates, etc.)

        Returns:
            Created production order response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/product/production"

        try:
            response = self.session.put(url, json=order_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error creating production order: {e}")
            raise

    def confirm_production_order(self, production_id: str) -> Dict[str, Any]:
        """
        Confirm a production order and move it to in_progress status
        This unlocks the first phase to ready-to-start

        Args:
            production_id: ID of the production order

        Returns:
            Confirmation response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/product/production/{production_id}/_confirm"

        try:
            response = self.session.post(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error confirming production order {production_id}: {e}")
            raise

    def schedule_production_phases(self, production_id: str) -> Dict[str, Any]:
        """
        Generate phase sequence for a production order

        Args:
            production_id: ID of the production order

        Returns:
            Phase sequence response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/production/{production_id}/_schedule"

        try:
            response = self.session.post(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error scheduling production phases: {e}")
            raise

    def start_phase(self, phase_id: str) -> Dict[str, Any]:
        """
        Start a production order phase

        Args:
            phase_id: ID of the production order phase

        Returns:
            Phase start response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/production-order-phase/{phase_id}/_start"

        try:
            response = self.session.post(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error starting phase: {e}")
            raise

    def complete_phase(self, phase_id: str) -> Dict[str, Any]:
        """
        Complete a production order phase

        Args:
            phase_id: ID of the production order phase

        Returns:
            Phase completion response

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/production-order-phase/{phase_id}/_complete"

        try:
            response = self.session.post(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error completing phase: {e}")
            raise
