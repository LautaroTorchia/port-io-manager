import argparse
import os
import glob
import json
from port_io_manager.client import PortAPIClient
from port_io_manager.comparator import BlueprintComparator
from port_io_manager.utils import sanitize_diff


def parse_cli_arguments():
    """Función para procesar los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Gestiona recursos de Port.io desde archivos JSON locales.")
    parser.add_argument('path', help="Ruta a un archivo .json o a un directorio que contenga archivos .json.")
    parser.add_argument('--force', action='store_true', help="Forzar la actualización, ignorando la fecha de última modificación.")
    return parser.parse_args()


def main():
    """Función principal que procesa los archivos de blueprints."""
    args = parse_cli_arguments()

    # Inicializa el cliente para interactuar con la API de Port.io
    client = PortAPIClient(
        client_id=os.getenv("PORT_CLIENT_ID"),
        client_secret=os.getenv("PORT_CLIENT_SECRET")
    )

    input_path = args.path
    json_files_to_process = []

    # Verifica si la ruta proporcionada es un archivo .json o un directorio
    if os.path.isfile(input_path) and input_path.endswith('.json'):
        json_files_to_process = [input_path]
    elif os.path.isdir(input_path):
        json_files_to_process = glob.glob(os.path.join(input_path, '*.json'))
    else:
        print(f"❌ Error: El archivo o directorio '{input_path}' no existe o no es válido.")
        return

    # Procesa cada archivo JSON encontrado
    for file_path in json_files_to_process:
        print(f"\nProcesando archivo: {file_path}")
        try:
            with open(file_path, 'r') as f:
                local_data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Error: El archivo '{file_path}' no es un JSON válido.")
            continue
        
        blueprint_id = local_data.get('identifier')
        print(blueprint_id)
        if not blueprint_id:
            print(f"❌ Error: El archivo '{file_path}' debe tener un 'identifier'.")
            continue

        # Obtener el blueprint remoto por su ID
        remote_data = client.get_resource(blueprint_id)
        # Verifica si el blueprint ya existe
        if remote_data:
            comparator = BlueprintComparator()
            diff = comparator.compare(local_data, remote_data)
            diff = sanitize_diff(diff)

            if diff:
                print("🔎 Diferencias encontradas:")
                print(diff)

                # Verifica si debe forzar la actualización
                if not args.force:
                    # Si el recurso fue actualizado en menos de 24 horas, se puede forzar la actualización
                    if not client.check_recent_update(remote_data, args.force):
                        user_input = input("¿Deseas continuar y sobreescribir los cambios remotos? (s/N): ")
                        if user_input.lower() != 's':
                            print("Operación abortada por el usuario.")
                            continue

                print(f"Actualizando blueprint con ID: {blueprint_id}")
                client.update_resource(blueprint_id, local_data)
            else:
                print(f"✅ El blueprint '{blueprint_id}' está sincronizado.")
        else:
            # Si el blueprint no existe, lo creamos
            print(f"🔨 Creando un nuevo blueprint con ID: {blueprint_id}")
            client.create_resource(local_data)


if __name__ == '__main__':
    main()
