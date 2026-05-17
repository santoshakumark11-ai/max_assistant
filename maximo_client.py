import os
import requests
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

class MaximoClient:
    def __init__(self):
        self.base_url = st.secrets["MAXIMO_BASE_URL"]
        #self.api_key = os.getenv("MAXIMO_API_KEY")
        self.api_key = st.secrets["API_KEY"]
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    def _get(self, endpoint: str, params: dict=None) -> dict:
        """Generate GET Request to Maximo API."""
        url = f"{self.base_url}/{endpoint}"
        default_params = {"lean": "1"}
        if params:
            default_params.update(params)
        response = requests.get(url, headers=self.headers, params=default_params, verify=True)
        response.raise_for_status()
        return response.json()

    def get_work_orders(self, where_clause: str = None, select: str = None, max_items: int = 10) -> list:
        """Fetch Work Orders from Maximo."""
        params = {}
        params['oslc.pageSize'] = 10
        if where_clause:
            params['oslc.where'] = where_clause
        if select:
            params['oslc.select'] = select

        result = self._get("os/mxapiwo", params=params)
        return result.get("member", [])
    
    def get_object_details(self, where_clause: str = None, select: str = '*', max_items: int = 10, object_name: str = None) -> list:
        params = {}
        params['oslc.pageSize'] = max_items
        if where_clause:
            params['oslc.where'] = where_clause
        if select:
            params['oslc.select'] = select

        if object_name is not None:
            if object_name.lower() == "workorder":
                object_name = "mxapiwodetail"
            elif object_name.lower() == "asset":
                object_name = "mxapiasset"
            elif object_name.lower() == "location":
                object_name = "mxapilocation"
            elif object_name.lower() == "sr":
                object_name = "mxapisr" 
            else:
                object_name = f"mxapi{object_name.lower()}"
            endpoint = f"os/{object_name}"

            result = self._get(endpoint, params=params)
            return result.get("member", [])
        else:
            raise ValueError("object_name must be provided for get_work_object_details")
        

    def search_non_work_orders_objects(self, where_clause: str = None, select: str = None, max_items: int = 10, object_name: str = None) -> list:
        params = {}
        params['oslc.pageSize'] = 1
        if where_clause:
            params['oslc.where'] = where_clause
        if select:
            params['oslc.select'] = select

        if object_name is not None:
            if object_name.lower() == "asset":
                object_name = "mxapiasset"
            elif object_name.lower() == "location":
                object_name = "mxapilocation"
            elif object_name.lower() == "sr":
                object_name = "mxapisr" 
            else:
                object_name = f"mxapi{object_name.lower()}"
            endpoint = f"os/{object_name}"

            result = self._get(endpoint, params=params)
            return result.get("member", [])
        else:
            raise ValueError("object_name must be provided for get_work_object_details")   
