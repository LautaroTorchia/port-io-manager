import json
import os
import sys
import requests
import glob
import argparse
from dotenv import load_dotenv
from deepdiff import DeepDiff
from datetime import datetime, timezone

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
# La AUTH_URL vuelve a ser la global, que es donde tus credenciales funcionan.
AUTH_URL = "https://api.port.io/v1/auth/access_token"
# MODIFICADO: La BASE_URL ahora también apunta al dominio global para ser consistente.
BASE_URL = "https://api.port.io/v1/blueprints"


class PortAPIClient:
    """Un cliente para interactuar con la API de Port.io."""
    
    def __init__(self, client_id, client_secret):
        if not client_id or not client_secret:
            print("Error: PORT_CLIENT_ID y PORT_CLIENT_SECRET deben estar definidos en el archivo .env.")
            sys.exit(1)

        self._client_id = client_id
        self._client_secret = client_secret
        self._session = requests.Session()
        self._authenticate()

    def _authenticate(self):
        """Obtiene un token de acceso y lo configura en la sesión."""
        payload = {"clientId": self._client_id, "clientSecret": self._client_secret}
        try:
            response = self._session.post(AUTH_URL, json=payload)
            response.raise_for_status()
            access_token = response.json()['accessToken']
            self._session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            })
            print("Autenticación exitosa.")
        except requests.exceptions.RequestException as e:
            print(f"Error de autenticación: {e}")
            if e.response: print(f"Detalle: {e.response.text}")
            sys.exit(1)

    def get_blueprint(self, blueprint_id):
        """Busca un blueprint por su ID."""
        url = f"{BASE_URL}/{blueprint_id}"
        try:
            response = self._session.get(url)
            if response.status_code == 404:
                print(f"Blueprint '{blueprint_id}' no encontrado.")
                return None
            response.raise_for_status()
            print(f"Blueprint '{blueprint_id}' encontrado.")
            return response.json().get("blueprint")
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener el blueprint: {e}")
            return None

    def create_blueprint(self, blueprint_data):
        """Crea un nuevo blueprint."""
        try:
            response = self._session.post(BASE_URL, data=json.dumps(blueprint_data))
            response.raise_for_status()
            print("✅ Blueprint creado con éxito.")
            print(json.dumps(response.json(), indent=2))
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al crear el blueprint: {e}")
            if e.response: print(f"Detalle: {e.response.text}")

    def update_blueprint(self, blueprint_id, blueprint_data):
        """Actualiza un blueprint existente."""
        url = f"{BASE_URL}/{blueprint_id}"
        # --- INICIO DE LA MODIFICACIÓN FINAL ---
        update_payload = blueprint_data.copy()

        # 1. Eliminar claves de nivel superior gestionadas por el servidor.
        top_level_keys_to_remove = ['createdAt', 'updatedAt', 'createdBy', 'updatedBy']
        for key in top_level_keys_to_remove:
            update_payload.pop(key, None)

        # 2. Eliminar propiedades con nombres reservados DENTRO del schema.
        # Esto previene que la API rechace definir propiedades que chocan con metadatos del sistema.
        if 'schema' in update_payload and 'properties' in update_payload['schema']:
            # Usamos la lista de propiedades que el diff indica que estás añadiendo.
            schema_properties_to_remove = [
                'createdAt', 'updatedAt', 'createdBy', 'updatedBy', 
                'resolvedAt', 'statusChangedAt'
            ]
            for key in schema_properties_to_remove:
                if key in update_payload['schema']['properties']:
                    # Elimina la propiedad reservada de la definición del schema
                    del update_payload['schema']['properties'][key]
        # --- FIN DE LA MODIFICACIÓN FINAL ---
        
        try:
            print(update_payload,url,self._session.headers)
            response = self._session.put(url, data=json.dumps(update_payload))
            response.raise_for_status()
            print("✅ Blueprint actualizado con éxito.")
            print(json.dumps(response.json(), indent=2))
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al actualizar el blueprint: {e}")
            if e.response: print(f"Detalle: {e.response.text}")



def format_diff_for_display(diff):
    """Formatea el objeto DeepDiff para una visualización clara y correcta."""
    processed_diff = {}
    if 'values_changed' in diff:
        processed_diff['values_changed'] = [
            {'key': key.replace("root", "blueprint"), 'remote_value': value['old_value'], 'local_value': value['new_value']}
            for key, value in diff['values_changed'].items()
        ]
    if 'dictionary_item_added' in diff:
        processed_diff['items_added_locally'] = [item.replace("root", "blueprint") for item in diff['dictionary_item_added']]
    if 'dictionary_item_removed' in diff:
        processed_diff['items_removed_locally'] = [item.replace("root", "blueprint") for item in diff['dictionary_item_removed']]
    return processed_diff


def compare_blueprints(local_blueprint, remote_blueprint):
    """Compara el blueprint local con el remoto y muestra las diferencias."""
    exclude_paths = ["root['createdAt']", "root['updatedAt']", "root['createdBy']", "root['updatedBy']"]
    diff = DeepDiff(remote_blueprint, local_blueprint, ignore_order=True, exclude_paths=exclude_paths)
    
    if not diff:
        print("✅ No se encontraron diferencias. El blueprint está sincronizado.")
        return None

    print("🔎 Diferencias encontradas:")
    formatted_diff = format_diff_for_display(diff)
    print(json.dumps(formatted_diff, indent=2, ensure_ascii=False))
    return formatted_diff


def check_recent_update(blueprint_metadata, force_update):
    """Verifica si el blueprint fue actualizado en la UI recientemente."""
    if force_update:
        print("Forzando la actualización (--force). Se ignorará la fecha de última modificación.")
        return True
    
    last_updated_str = blueprint_metadata.get('updatedAt')
    if not last_updated_str: return True

    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
    time_difference = datetime.now(timezone.utc) - last_updated
    
    print(f"Última actualización remota: {last_updated}")
    if time_difference.total_seconds() < 86400: # Menos de 24 horas
        print("⚠️  ¡Advertencia! El blueprint ha sido actualizado desde la UI hace menos de 24 horas.")
        return False
    return True

def process_blueprint_file(file_path, client, force_update):
    """Carga, compara y actualiza un único blueprint a partir de su archivo JSON."""
    print(f"\n{'='*20} \n📂 Procesando: {os.path.basename(file_path)} \n{'='*20}")
    
    try:
        with open(file_path, 'r') as f:
            local_blueprint_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo '{file_path}' no es un JSON válido. Saltando al siguiente.")
        return

    blueprint_id = local_blueprint_data.get('identifier')
    if not blueprint_id:
        print(f"❌ Error: El JSON en '{file_path}' debe tener la clave 'identifier'. Saltando al siguiente.")
        return

    remote_blueprint = client.get_blueprint(blueprint_id)

    if remote_blueprint:
        diff = compare_blueprints(local_blueprint_data, remote_blueprint)
        if not diff:
            return

        if not check_recent_update(remote_blueprint, force_update):
            user_input = input("¿Deseas continuar y sobreescribir los cambios remotos? (s/N): ")
            if user_input.lower() != 's':
                print("Operación abortada por el usuario para este archivo.")
                return
        
        print(f"Actualizando el blueprint '{blueprint_id}'...")
        client.update_blueprint(blueprint_id, local_blueprint_data)
    else:
        print(f"Creando un nuevo blueprint '{blueprint_id}'...")
        client.create_blueprint(local_blueprint_data)


def main():
    parser = argparse.ArgumentParser(description="Gestiona blueprints de Port.io desde archivos JSON locales.")
    parser.add_argument('path', help="Ruta a un archivo .json o a un directorio que contenga archivos .json.")
    parser.add_argument('--force', action='store_true', help="Forzar la actualización, ignorando la fecha de última modificación.")
    args = parser.parse_args()

    client = PortAPIClient(
        client_id=os.getenv("PORT_CLIENT_ID"),
        client_secret=os.getenv("PORT_CLIENT_SECRET")
    )

    input_path = args.path
    json_files_to_process = []

    if not os.path.exists(input_path):
        print(f"❌ Error: La ruta '{input_path}' no existe.")
        sys.exit(1)

    if os.path.isfile(input_path):
        if input_path.endswith('.json'):
            json_files_to_process.append(input_path)
        else:
            print(f"❌ Error: El archivo '{input_path}' no es un archivo .json.")
            sys.exit(1)
    elif os.path.isdir(input_path):
        search_path = os.path.join(input_path, '*.json')
        json_files_to_process = glob.glob(search_path)
        if not json_files_to_process:
            print(f"ℹ️ No se encontraron archivos .json en el directorio '{input_path}'.")
            return

    total_files = len(json_files_to_process)
    print(f"\n🚀 Se procesarán {total_files} blueprint(s).")

    for file_path in json_files_to_process:
        process_blueprint_file(file_path, client, args.force)
    
    print(f"\n✨ Proceso completado. Se han procesado {total_files} archivo(s).")


if __name__ == '__main__':
    main()