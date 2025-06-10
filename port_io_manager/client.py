import requests
import sys
import os
from dotenv import load_dotenv
import json

load_dotenv()

AUTH_URL = "https://api.port.io/v1/auth/access_token"
BASE_URL = "https://api.port.io/v1/blueprints"

class PortAPIClient:
    """Cliente Singleton para interactuar con la API de Port.io."""

    _instance = None

    def __new__(cls, client_id=None, client_secret=None):
        """Implementación del patrón Singleton para la clase PortAPIClient."""
        if cls._instance is None:
            if not client_id or not client_secret:
                print("Error: PORT_CLIENT_ID y PORT_CLIENT_SECRET deben estar definidos en el archivo .env.")
                sys.exit(1)
            cls._instance = super(PortAPIClient, cls).__new__(cls)
            cls._instance._client_id = client_id
            cls._instance._client_secret = client_secret
            cls._instance._session = requests.Session()
            cls._instance._authenticate()
        return cls._instance

    def _authenticate(self):
        """Obtiene un token de acceso y lo configura en la sesión."""
        payload = {"clientId": self._client_id, "clientSecret": self._client_secret}
        try:
            response = requests.post(AUTH_URL, json=payload)
            response.raise_for_status()
            access_token = response.json()['accessToken']
            self._session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            })
            print("Autenticación exitosa.")
        except requests.exceptions.RequestException as e:
            print(f"Error de autenticación: {e}")
            sys.exit(1)

    def get_resource(self, resource_id):
        """Busca un recurso por su ID."""
        url = f"{BASE_URL}/{resource_id}"  # Corregido
        try:
            response = self._session.get(url)
            response.raise_for_status()
            return response.json().get("resource")
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener el recurso con ID {resource_id}: {e}")
            return None

    def create_resource(self, resource_data):
        """Crea un nuevo recurso."""
        url = BASE_URL
        try:
            response = self._session.post(url, data=json.dumps(resource_data))
            response.raise_for_status()
            print("✅ Recurso creado con éxito.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al crear el recurso: {e}")
            if e.response:
                print(f"Detalle: {e.response.text}")

    def update_resource(self, resource_id, resource_data):
        """Actualiza un recurso existente."""
        url = f"{BASE_URL}/{resource_id}"  # Corregido
        try:
            response = self._session.put(url, data=json.dumps(resource_data))
            response.raise_for_status()
            print("✅ Recurso actualizado con éxito.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al actualizar el recurso: {e}")
            if e.response:
                print(f"Detalle: {e.response.text}")