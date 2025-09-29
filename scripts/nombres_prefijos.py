import os
import re
from datetime import datetime

class ImageRenamer:
    def __init__(self, input_folder):
        """
        Inicializa la clase para renombrar imágenes.
        
        Args:
            input_folder (str): La ruta a la carpeta que contiene las imágenes.
        """
        self.input_folder = os.path.abspath(input_folder)
        
        if not os.path.isdir(self.input_folder):
            raise FileNotFoundError(f"❌ Error: La carpeta '{self.input_folder}' no existe.")
            
        self.folder_prefix = self.extract_folder_prefix(self.input_folder)
        self.image_counter = 1
        
        print(f"📁 Analizando la carpeta: {self.input_folder}")
        print(f"🏷️ Prefijo a utilizar: {self.folder_prefix}")
        print("-" * 50)
        
    def extract_folder_prefix(self, folder_path):
        """
        Extrae y limpia un prefijo del nombre de la carpeta.
        Se basa en la lógica de tu código original.
        """
        folder_name = os.path.basename(folder_path)
        
        # Limpiar caracteres especiales y espacios
        cleaned_name = re.sub(r'[^\w\s-]', '', folder_name)
        
        # Reemplazar espacios y guiones múltiples con guión bajo
        cleaned_name = re.sub(r'[\s_-]+', '_', cleaned_name)
        
        # Convertir a CamelCase y limitar la longitud
        words = cleaned_name.split('_')
        camel_case = ''.join(word.capitalize() for word in words if word)
        
        # Si aún es muy largo, truncar
        if len(camel_case) > 20:
            camel_case = camel_case[:20]
        
        if not camel_case:
            return "Carpeta"
            
        return camel_case
        
    def parse_filename(self, filename):
        """
        Extrae el número de pregunta, página y tipo de contenido del nombre de archivo original.
        Es lo suficientemente flexible para encontrar patrones comunes.
        """
        data = {
            "question": None, # Cambiado a None para mejor control
            "page": None,    # Cambiado a None
            "type": None,    # Cambiado a None
        }
        
        # Expresión para encontrar el número de pregunta (Pregunta_XX)
        question_match = re.search(r'Pregunta_(\d+)', filename, re.IGNORECASE)
        if question_match:
            data['question'] = question_match.group(1)
        
        # Expresión para encontrar el tipo de contenido (Cientifica o General)
        type_match = re.search(r'(Cientifica)', filename, re.IGNORECASE)
        if type_match:
            data['type'] = type_match.group(1).capitalize()
            
        # Expresión para encontrar el número de página (PagYY)
        page_match = re.search(r'Pag(\d+)', filename, re.IGNORECASE)
        if page_match:
            data['page'] = page_match.group(1)
            
        return data

    def get_file_info(self):
        """
        Obtiene una lista de los archivos en la carpeta, ordenada por fecha de creación.
        """
        files = []
        for f in os.listdir(self.input_folder):
            if os.path.isfile(os.path.join(self.input_folder, f)):
                files.append(f)
        
        # Ordenar los archivos por fecha de creación
        files.sort(key=lambda f: os.path.getctime(os.path.join(self.input_folder, f)))
        
        return files
        
    def rename_files(self):
        """
        Renombra todos los archivos de imagen en la carpeta.
        """
        files_to_rename = self.get_file_info()
        
        if not files_to_rename:
            print("❗ No se encontraron archivos para renombrar.")
            return

        print(f"📦 Se encontraron {len(files_to_rename)} archivos para procesar.")
        
        renamed_count = 0
        for old_filename in files_to_rename:
            try:
                # Omitir el script de Python si está en la misma carpeta
                if old_filename.endswith('.py'):
                    continue
                
                # Obtener la extensión del archivo
                name, ext = os.path.splitext(old_filename)
                ext = ext.lstrip('.').lower()
                
                # Obtener la información del nombre de archivo original
                parsed_data = self.parse_filename(name)
                
                # Construir el nuevo nombre de archivo de forma dinámica
                parts = [f"{self.image_counter:03d}", self.folder_prefix]
                
                if parsed_data['question']:
                    parts.append(f"Pregunta_{parsed_data['question']}")
                
                if parsed_data['type']:
                    parts.append(parsed_data['type'])
                
                if parsed_data['page']:
                    parts.append(f"Pag{parsed_data['page']}")
                    
                new_filename = "_".join(parts) + f".{ext}"
                
                old_filepath = os.path.join(self.input_folder, old_filename)
                new_filepath = os.path.join(self.input_folder, new_filename)
                
                # Renombrar el archivo
                os.rename(old_filepath, new_filepath)
                
                print(f"✅ Renombrado: {old_filename} -> {new_filename}")
                self.image_counter += 1
                renamed_count += 1
                
            except Exception as e:
                print(f"❌ Error al procesar {old_filename}: {e}")
                
        print("-" * 50)
        print(f"🎉 Proceso completado. Se renombraron {renamed_count} archivos.")
        
# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    # --- Modifica esta variable con la ruta de tu carpeta ---
    # Ejemplo con tu ruta específica:
    ruta_carpeta_a_renombrar = r"C:\Users\natus\Documents\Trabajo\PEDRO_PEREZ\ICFES\Lectura Critica\Imagenes_Lectura_Critica\S11-C primera sesión _"
    
    try:
        renamer = ImageRenamer(ruta_carpeta_a_renombrar)
        renamer.rename_files()
    except FileNotFoundError as e:
        print(e)