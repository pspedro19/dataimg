import fitz  # PyMuPDF
import os
import re
from PIL import Image
import io

class PDFImageExtractor:
    def __init__(self, pdf_path, output_folder="extracted_images", banco_preguntas="BancoPreguntas"):
        self.pdf_path = pdf_path
        self.output_folder = os.path.abspath(output_folder)  # Convertir a ruta absoluta
        self.doc = None
        self.image_counter = 1
        
        # Limpiar y formatear el nombre del banco de preguntas
        self.banco_preguntas = self.clean_banco_name(banco_preguntas)
        
        # Extraer y limpiar el nombre del PDF para usar como prefijo
        self.pdf_prefix = self.extract_pdf_prefix(pdf_path)
        
        # Crear carpeta de salida si no existe
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"📁 Carpeta creada: {self.output_folder}")
        else:
            print(f"📁 Usando carpeta existente: {self.output_folder}")
        
        print(f"🎯 UBICACIÓN CONFIRMADA DE ARCHIVOS DE SALIDA:")
        print(f"   {self.output_folder}")
        print(f"🏦 BANCO DE PREGUNTAS: {self.banco_preguntas}")
        print(f"🏷️  PREFIJO DEL PDF: {self.pdf_prefix}")
        print(f"{'='*60}")
    
    def clean_banco_name(self, banco_name):
        """
        Limpiar y formatear el nombre del banco de preguntas
        """
        if not banco_name:
            return "BancoPreguntas"
        
        # Limpiar caracteres especiales y espacios
        cleaned = re.sub(r'[^\w\s-]', '', banco_name)
        
        # Reemplazar espacios con nada (CamelCase)
        words = cleaned.split()
        camel_case = ''.join(word.capitalize() for word in words if word)
        
        # Limitar longitud (máximo 15 caracteres para el banco)
        if len(camel_case) > 15:
            camel_case = camel_case[:15]
        
        # Asegurar que no esté vacío
        if not camel_case:
            camel_case = "BancoPreguntas"
        
        return camel_case
    
    def extract_pdf_prefix(self, pdf_path):
        """
        Extraer un prefijo limpio del nombre del archivo PDF
        """
        # Obtener solo el nombre del archivo (sin ruta ni extensión)
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Limpiar el nombre del archivo
        # Remover caracteres especiales y espacios
        cleaned_name = re.sub(r'[^\w\s-]', '', filename)
        
        # Reemplazar espacios y guiones múltiples con guión bajo
        cleaned_name = re.sub(r'[\s_-]+', '_', cleaned_name)
        
        # Convertir a formato CamelCase para hacerlo más compacto
        words = cleaned_name.split('_')
        camel_case = ''.join(word.capitalize() for word in words if word)
        
        # Limitar longitud del prefijo (máximo 20 caracteres)
        if len(camel_case) > 20:
            # Tomar las primeras letras de cada palabra importante
            important_words = []
            for word in words:
                if len(word) > 3:  # Solo palabras importantes
                    important_words.append(word)
            
            if important_words:
                # Crear abreviación
                if len(important_words) <= 3:
                    camel_case = ''.join(word.capitalize()[:4] for word in important_words)
                else:
                    camel_case = ''.join(word.capitalize()[:3] for word in important_words[:4])
            
            # Si aún es muy largo, truncar
            if len(camel_case) > 20:
                camel_case = camel_case[:20]
        
        # Asegurar que no esté vacío
        if not camel_case:
            camel_case = "PDF"
        
        return camel_case
    
    def open_pdf(self):
        """Abrir el documento PDF"""
        try:
            self.doc = fitz.open(self.pdf_path)
            print(f"PDF abierto exitosamente: {len(self.doc)} páginas")
            return True
        except Exception as e:
            print(f"Error al abrir el PDF: {e}")
            return False
    
    def extract_question_from_text(self, text, image_position):
        """
        Extraer el nombre/número de la pregunta del texto
        Adaptado específicamente para el formato del PDF de ciencias naturales
        """
        # Patrón específico para este PDF: "1.21 Pregunta 21", "1.22 Pregunta 22", etc.
        patterns = [
            r'1\.(\d+)\s+Pregunta\s+(\d+)',  # Formato exacto del PDF
            r'Pregunta\s+(\d+)',  # Formato simplificado
            r'(\d+)\s+Pregunta\s+(\d+)',  # Variación más general
            r'Pregunta\s*(\d+)',  # Patrón más flexible
        ]
        
        # Buscar el patrón más específico primero
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if len(matches[0]) == 2:  # Para patrones que capturan dos números
                    # Usar el segundo número (número de pregunta)
                    return f"Pregunta_{matches[-1][1]}"
                else:  # Para patrones que capturan un número
                    return f"Pregunta_{matches[-1]}"
        
        # Buscar números de pregunta en líneas específicas
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Buscar líneas que contengan números de pregunta
            if 'Pregunta' in line:
                number_match = re.search(r'Pregunta\s+(\d+)', line, re.IGNORECASE)
                if number_match:
                    return f"Pregunta_{number_match.group(1)}"
            
            # Buscar formato "1.XX Pregunta XX"
            format_match = re.search(r'1\.(\d+)', line)
            if format_match:
                return f"Pregunta_{format_match.group(1)}"
        
        # Buscar cualquier número que podría ser una pregunta
        numbers = re.findall(r'\b(\d{1,2})\b', text)
        if numbers:
            # Filtrar números que podrían ser números de pregunta (entre 1 y 50)
            valid_numbers = [num for num in numbers if 1 <= int(num) <= 50]
            if valid_numbers:
                return f"Pregunta_{valid_numbers[-1]}"
        
        return f"Pregunta_Desconocida"
    
    def get_surrounding_text(self, page, image_rect, context_margin=100):
        """
        Obtener texto alrededor de la imagen para identificar la pregunta
        Optimizado para PDFs de ciencias naturales
        """
        # Expandir el área de búsqueda alrededor de la imagen
        search_rect = fitz.Rect(
            max(0, image_rect.x0 - context_margin),
            max(0, image_rect.y0 - context_margin*3),  # Buscar más arriba para encontrar el título de la pregunta
            min(page.rect.width, image_rect.x1 + context_margin),
            min(page.rect.height, image_rect.y1 + context_margin)
        )
        
        # Extraer texto del área expandida
        surrounding_text = page.get_text("text", clip=search_rect)
        
        # También obtener texto de toda la página para contexto adicional
        full_page_text = page.get_text("text")
        
        # Buscar específicamente el texto antes de la imagen (donde suelen estar los títulos)
        above_image_rect = fitz.Rect(
            0,  # Desde el inicio de la página
            max(0, image_rect.y0 - context_margin*2),
            page.rect.width,  # Hasta el final del ancho
            image_rect.y0  # Hasta donde empieza la imagen
        )
        
        above_text = page.get_text("text", clip=above_image_rect)
        
        return surrounding_text + "\n" + above_text, full_page_text
    
    def is_scientific_content(self, surrounding_text):
        """
        Determinar si la imagen podría ser contenido científico
        """
        scientific_keywords = [
            'química', 'física', 'biología', 'fórmula', 'ecuación',
            'gráfico', 'tabla', 'diagrama', 'elemento', 'molécula',
            'átomo', 'reacción', 'experimento', 'laboratorio', 'ácido',
            'base', 'pH', 'temperatura', 'presión', 'volumen', 'masa',
            'velocidad', 'aceleración', 'fuerza', 'energía'
        ]
        
        text_lower = surrounding_text.lower()
        return any(keyword in text_lower for keyword in scientific_keywords)
    
    def extract_images_from_page(self, page_num):
        """Extraer todas las imágenes de una página específica"""
        page = self.doc[page_num]
        image_list = page.get_images()
        
        extracted_images = []
        
        for img_index, img in enumerate(image_list):
            try:
                # Obtener referencia de la imagen
                xref = img[0]
                
                # Extraer la imagen
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Filtrar imágenes muy pequeñas (probablemente decorativas)
                if base_image["width"] < 50 or base_image["height"] < 50:
                    print(f"Imagen {img_index + 1} de la página {page_num + 1} omitida (muy pequeña: {base_image['width']}x{base_image['height']})")
                    continue
                
                # Obtener información de posición de la imagen
                image_rects = page.get_image_rects(img)
                if image_rects:
                    image_rect = image_rects[0]  # Usar la primera posición encontrada
                else:
                    image_rect = fitz.Rect(0, 0, 100, 100)  # Rectángulo por defecto
                
                # Obtener texto circundante para identificar la pregunta
                surrounding_text, full_page_text = self.get_surrounding_text(page, image_rect)
                
                # Identificar la pregunta
                question_name = self.extract_question_from_text(
                    surrounding_text + "\n" + full_page_text, 
                    image_rect
                )
                
                # Determinar si es contenido científico
                is_scientific = self.is_scientific_content(surrounding_text + full_page_text)
                content_type = "Cientifica" if is_scientific else "General"
                
                # Crear nombre del archivo completo con banco de preguntas y prefijo del PDF
                filename = f"{self.image_counter:03d}_{self.banco_preguntas}_{self.pdf_prefix}_{question_name}_{content_type}_Pag{page_num+1}.{image_ext}"
                filepath = os.path.join(self.output_folder, filename)
                
                # Guardar la imagen
                with open(filepath, "wb") as image_file:
                    image_file.write(image_bytes)
                
                # Información de la imagen extraída
                image_info = {
                    'numero': self.image_counter,
                    'pagina': page_num + 1,
                    'archivo': filename,
                    'banco_preguntas': self.banco_preguntas,
                    'prefijo_pdf': self.pdf_prefix,
                    'pregunta': question_name,
                    'tipo_contenido': content_type,
                    'posicion': (round(image_rect.x0, 2), round(image_rect.y0, 2)),
                    'tamaño': f"{base_image['width']}x{base_image['height']}",
                    'formato': image_ext,
                    'texto_contexto': surrounding_text[:200] + "..." if len(surrounding_text) > 200 else surrounding_text
                }
                
                extracted_images.append(image_info)
                print(f"✅ Imagen {self.image_counter} extraída: {filename}")
                
                self.image_counter += 1
                
            except Exception as e:
                print(f"❌ Error al extraer imagen {img_index + 1} de la página {page_num + 1}: {e}")
        
        return extracted_images
    
    def extract_all_images(self):
        """Extraer todas las imágenes del PDF"""
        if not self.open_pdf():
            return []
        
        all_extracted_images = []
        
        print(f"Iniciando extracción de imágenes de {len(self.doc)} páginas...")
        
        for page_num in range(len(self.doc)):
            print(f"\nProcesando página {page_num + 1}...")
            page_images = self.extract_images_from_page(page_num)
            all_extracted_images.extend(page_images)
        
        print(f"\n¡Extracción completada! Total de imágenes extraídas: {len(all_extracted_images)}")
        
        # Generar reporte
        self.generate_report(all_extracted_images)
        
        return all_extracted_images
    
    def generate_report(self, images):
        """Generar un reporte detallado de las imágenes extraídas"""
        report_path = os.path.join(self.output_folder, "reporte_extraccion.txt")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("="*70 + "\n")
            f.write("REPORTE DETALLADO DE EXTRACCIÓN DE IMÁGENES\n")
            f.write("PDF de Ciencias Naturales - Ejercicios Resueltos\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"📁 PDF procesado: {self.pdf_path}\n")
            f.write(f"🏦 Banco de preguntas: {self.banco_preguntas}\n")
            f.write(f"🏷️  Prefijo utilizado: {self.pdf_prefix}\n")
            f.write(f"🖼️  Total de imágenes extraídas: {len(images)}\n")
            f.write(f"📂 Carpeta de destino: {self.output_folder}\n")
            f.write(f"📅 Fecha de procesamiento: {os.popen('date /t').read().strip()}\n\n")
            
            # Estadísticas por tipo de contenido
            cientificas = [img for img in images if img.get('tipo_contenido') == 'Cientifica']
            generales = [img for img in images if img.get('tipo_contenido') == 'General']
            
            f.write("📊 ESTADÍSTICAS:\n")
            f.write(f"   • Imágenes científicas: {len(cientificas)}\n")
            f.write(f"   • Imágenes generales: {len(generales)}\n\n")
            
            # Estadísticas por formato
            formatos = {}
            for img in images:
                formato = img['formato']
                formatos[formato] = formatos.get(formato, 0) + 1
            
            f.write("📈 FORMATOS DE IMAGEN:\n")
            for formato, cantidad in formatos.items():
                f.write(f"   • {formato.upper()}: {cantidad} imágenes\n")
            f.write("\n")
            
            # Distribución por páginas
            paginas = {}
            for img in images:
                pag = img['pagina']
                paginas[pag] = paginas.get(pag, 0) + 1
            
            f.write("📄 DISTRIBUCIÓN POR PÁGINAS:\n")
            for pag in sorted(paginas.keys()):
                f.write(f"   • Página {pag}: {paginas[pag]} imágenes\n")
            f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("DETALLE DE IMÁGENES EXTRAÍDAS\n")
            f.write("="*70 + "\n\n")
            
            for i, img in enumerate(images, 1):
                f.write(f"IMAGEN #{img['numero']} (#{i} en secuencia)\n")
                f.write(f"{'─'*50}\n")
                f.write(f"📄 Archivo: {img['archivo']}\n")
                f.write(f"🏷️  Prefijo: {img.get('prefijo_pdf', 'No definido')}\n")
                f.write(f"📍 Página: {img['pagina']}\n")
                f.write(f"🔢 Pregunta: {img['pregunta']}\n")
                f.write(f"🧪 Tipo: {img.get('tipo_contenido', 'No clasificado')}\n")
                f.write(f"📐 Posición: {img['posicion']}\n")
                f.write(f"📏 Tamaño: {img['tamaño']} píxeles\n")
                f.write(f"🎨 Formato: {img['formato'].upper()}\n")
                
                if 'texto_contexto' in img and img['texto_contexto'].strip():
                    f.write(f"📝 Contexto: {img['texto_contexto']}\n")
                
                f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("INSTRUCCIONES DE USO\n")
            f.write("="*70 + "\n")
            f.write("FORMATO DE NOMBRES:\n")
            f.write("NNN_PrefijoDelPDF_Pregunta_XX_TipoContenido_PagYY.ext\n\n")
            f.write("EXPLICACIÓN:\n")
            f.write("• NNN: Número secuencial (001, 002, 003...)\n")
            f.write(f"• PrefijoDelPDF: {self.pdf_prefix} (derivado del nombre del PDF)\n")
            f.write("• Pregunta_XX: Número de pregunta identificado automáticamente\n")
            f.write("• TipoContenido: 'Cientifica' (fórmulas/gráficos) o 'General' (decorativa)\n")
            f.write("• PagYY: Número de página donde se encontró la imagen\n")
            f.write("• ext: Formato original (png, jpg, etc.)\n\n")
            f.write("VENTAJAS DEL PREFIJO:\n")
            f.write("• Diferencia imágenes de múltiples PDFs\n")
            f.write("• Evita confusión entre preguntas con mismos números\n")
            f.write("• Facilita organización de grandes volúmenes de imágenes\n")
            f.write("• Permite identificar rápidamente la fuente del documento\n\n")
            f.write("💡 SUGERENCIAS:\n")
            f.write("• Revisa las imágenes 'Sin_Identificar' para renombrarlas manualmente\n")
            f.write("• Las imágenes científicas suelen ser las más importantes\n")
            f.write("• Verifica que no falten imágenes de preguntas específicas\n")
            f.write("• El prefijo ayuda a organizar imágenes de múltiples documentos\n")
        
        print(f"📄 Reporte detallado generado: {report_path}")
    
    def close(self):
        """Cerrar el documento PDF"""
        if self.doc:
            self.doc.close()

# Función principal para uso fácil
def extraer_imagenes_pdf(pdf_path, output_folder="extracted_images"):
    """
    Función principal para extraer imágenes de un PDF
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        output_folder (str): Carpeta donde guardar las imágenes
    
    Returns:
        list: Lista de información de las imágenes extraídas
    """
    extractor = PDFImageExtractor(pdf_path, output_folder)
    try:
        images = extractor.extract_all_images()
        return images
    finally:
        extractor.close()

# Ejemplo de uso específico para el PDF de Ciencias Naturales
if __name__ == "__main__":
    # Ruta específica del PDF proporcionada por el usuario
    pdf_file = r"C:\Users\natus\Documents\Trabajo\PEDRO_PEREZ\ICFES\Lectura Critica\LECTURA CRITICA JUAN CAMILO ISAZA GUTIERREZ.pdf"
    
    # RUTA ABSOLUTA ESPECÍFICA - se guardará SÍ O SÍ en esta ubicación
    output_dir = r"C:\Users\natus\Documents\Trabajo\PEDRO_PEREZ\ICFES\Lectura Critica\imagenes_Lectura_Critica"
    
    # Función para crear nombre de archivo más descriptivo
    def crear_nombre_archivo(numero_imagen, pregunta, pagina, extension):
        # Limpiar el nombre de la pregunta
        pregunta_limpia = pregunta.replace("Pregunta_", "").replace("Pregunta_Desconocida", "Sin_Identificar")
        return f"{numero_imagen:03d}_Pregunta_{pregunta_limpia}_Pag_{pagina}.{extension}"
    
    if os.path.exists(pdf_file):
        print(f"🔍 Procesando: {pdf_file}")
        print(f"📂 Carpeta de salida CONFIRMADA: {output_dir}")
        print(f"📍 Ruta absoluta: {os.path.abspath(output_dir)}")
        
        # Mostrar preview del prefijo que se usará
        filename = os.path.splitext(os.path.basename(pdf_file))[0]
        cleaned_name = re.sub(r'[^\w\s-]', '', filename)
        cleaned_name = re.sub(r'[\s_-]+', '_', cleaned_name)
        words = cleaned_name.split('_')
        preview_prefix = ''.join(word.capitalize() for word in words if word)[:20]
        if not preview_prefix:
            preview_prefix = "PDF"
        
        print(f"🏷️  PREFIJO QUE SE USARÁ: {preview_prefix}")
        print(f"📝 EJEMPLO DE NOMBRE: 001_{preview_prefix}_Pregunta_21_Cientifica_Pag2.png")
        print("-" * 70)
        
        imagenes = extraer_imagenes_pdf(pdf_file, output_dir)
        
        print(f"\n{'='*70}")
        print(f"✅ EXTRACCIÓN COMPLETADA EXITOSAMENTE")
        print(f"{'='*70}")
        print(f"📁 PDF procesado: {os.path.basename(pdf_file)}")
        print(f"🖼️  Imágenes extraídas: {len(imagenes)}")
        print(f"📂 Carpeta de salida: {os.path.abspath(output_dir)}")
        print(f"📄 Reporte generado: {os.path.join(output_dir, 'reporte_extraccion.txt')}")
        
        if imagenes:
            print(f"\n📋 PRIMERAS 5 IMÁGENES EXTRAÍDAS:")
            for i, img in enumerate(imagenes[:5], 1):
                ruta_completa = os.path.join(output_dir, img['archivo'])
                print(f"  {i:2d}. {img['archivo']}")
                print(f"      📍 {ruta_completa}")
            
            if len(imagenes) > 5:
                print(f"  ... y {len(imagenes) - 5} imágenes más")
        
        print(f"\n🎯 UBICACIÓN FINAL DE TUS ARCHIVOS:")
        print(f"   {os.path.abspath(output_dir)}")
        print(f"✅ ¡Proceso completado exitosamente!")
        
    else:
        print(f"❌ Error: No se encontró el archivo")
        print(f"📁 Ruta buscada: {pdf_file}")
        print("📝 Verifica que:")
        print("   1. El archivo existe")
        print("   2. La ruta es correcta")
        print("   3. Tienes permisos de lectura")
        
    input("\n⏸️  Presiona Enter para continuar...")