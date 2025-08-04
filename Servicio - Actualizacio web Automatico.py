"""
Sistema de Actualización Automatizada de Contenido Web
Departamento de Sistemas y Computación - ITM
Autor: Jordan Rivera Rodriguez
Fecha: Mayo 2025

Este módulo automatiza la actualización de contenido en la página web del departamento,
incluyendo la publicación de noticias, documentos y recursos.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import hashlib
import time
from typing import Dict, List, Optional


class ActualizadorWebDepartamental:
    """
    Gestiona la actualización automatizada de contenido en la página web departamental.
    
    Esta clase proporciona métodos para cargar, procesar y publicar contenido
    de manera segura y eficiente en el sistema de gestión de contenidos.
    """
    
    def __init__(self, url_base: str, api_key: str):
        """
        Inicializa el actualizador web.
        
        Args:
            url_base (str): URL base del sitio web departamental
            api_key (str): Clave API para autenticación
        """
        self.url_base = url_base
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self.log_file = 'actualizaciones_web.log'
        
    def _registrar_log(self, mensaje: str, nivel: str = 'INFO'):
        """
        Registra eventos en el archivo de log.
        
        Args:
            mensaje (str): Mensaje a registrar
            nivel (str): Nivel de log (INFO, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {nivel}: {mensaje}\n")
    
    def validar_contenido(self, contenido: Dict) -> bool:
        """
        Valida que el contenido cumpla con los requisitos antes de publicar.
        
        Args:
            contenido (dict): Diccionario con el contenido a validar
            
        Returns:
            bool: True si el contenido es válido, False en caso contrario
        """
        campos_requeridos = ['titulo', 'contenido', 'categoria', 'autor']
        
        # Verificar campos requeridos
        for campo in campos_requeridos:
            if campo not in contenido or not contenido[campo]:
                self._registrar_log(f"Campo requerido faltante: {campo}", "ERROR")
                return False
        
        # Validar longitud del título
        if len(contenido['titulo']) > 200:
            self._registrar_log("Título excede longitud máxima de 200 caracteres", "ERROR")
            return False
        
        # Validar categoría
        categorias_validas = ['noticias', 'eventos', 'avisos', 'recursos', 'documentos']
        if contenido['categoria'] not in categorias_validas:
            self._registrar_log(f"Categoría inválida: {contenido['categoria']}", "ERROR")
            return False
        
        return True
    
    def generar_slug(self, titulo: str) -> str:
        """
        Genera un slug URL-friendly a partir del título.
        
        Args:
            titulo (str): Título del contenido
            
        Returns:
            str: Slug generado
        """
        # Convertir a minúsculas y reemplazar caracteres especiales
        slug = titulo.lower()
        caracteres_reemplazo = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', ' ': '-', '/': '-', '\\': '-'
        }
        
        for char, reemplazo in caracteres_reemplazo.items():
            slug = slug.replace(char, reemplazo)
        
        # Eliminar caracteres no alfanuméricos
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Eliminar guiones múltiples
        while '--' in slug:
            slug = slug.replace('--', '-')
        
        # Agregar timestamp para unicidad
        timestamp = datetime.now().strftime('%Y%m%d')
        slug = f"{slug}-{timestamp}"
        
        return slug
    
    def procesar_imagenes(self, contenido_html: str) -> str:
        """
        Procesa y optimiza las imágenes en el contenido HTML.
        
        Args:
            contenido_html (str): HTML con imágenes a procesar
            
        Returns:
            str: HTML con imágenes procesadas y optimizadas
        """
        soup = BeautifulSoup(contenido_html, 'html.parser')
        imagenes = soup.find_all('img')
        
        for img in imagenes:
            if 'src' in img.attrs:
                # Agregar atributos de optimización
                img['loading'] = 'lazy'
                img['decoding'] = 'async'
                
                # Asegurar texto alternativo
                if 'alt' not in img.attrs or not img['alt']:
                    img['alt'] = 'Imagen del Departamento de Sistemas y Computación'
                
                # Agregar clases CSS para responsive
                clases = img.get('class', [])
                if 'img-fluid' not in clases:
                    clases.append('img-fluid')
                img['class'] = clases
        
        return str(soup)
    
    def publicar_contenido(self, contenido: Dict) -> Optional[Dict]:
        """
        Publica contenido en la página web del departamento.
        
        Args:
            contenido (dict): Diccionario con el contenido a publicar
            
        Returns:
            dict: Respuesta del servidor si es exitoso, None si falla
        """
        # Validar contenido
        if not self.validar_contenido(contenido):
            return None
        
        # Preparar datos para publicación
        contenido['slug'] = self.generar_slug(contenido['titulo'])
        contenido['fecha_publicacion'] = datetime.now().isoformat()
        contenido['contenido'] = self.procesar_imagenes(contenido['contenido'])
        
        # Calcular checksum para verificación
        contenido_str = json.dumps(contenido, sort_keys=True)
        contenido['checksum'] = hashlib.md5(contenido_str.encode()).hexdigest()
        
        try:
            # Enviar solicitud de publicación
            endpoint = f"{self.url_base}/api/contenido/publicar"
            respuesta = self.session.post(endpoint, json=contenido)
            
            if respuesta.status_code == 201:
                self._registrar_log(f"Contenido publicado exitosamente: {contenido['titulo']}")
                return respuesta.json()
            else:
                self._registrar_log(
                    f"Error al publicar: {respuesta.status_code} - {respuesta.text}", 
                    "ERROR"
                )
                return None
                
        except Exception as e:
            self._registrar_log(f"Excepción al publicar contenido: {str(e)}", "ERROR")
            return None
    
    def actualizar_contenido_masivo(self, archivo_json: str):
        """
        Actualiza múltiples contenidos desde un archivo JSON.
        
        Args:
            archivo_json (str): Ruta al archivo JSON con contenidos
        """
        try:
            with open(archivo_json, 'r', encoding='utf-8') as f:
                contenidos = json.load(f)
            
            total = len(contenidos)
            exitosos = 0
            
            print(f"Iniciando actualización masiva de {total} contenidos...")
            
            for i, contenido in enumerate(contenidos, 1):
                print(f"Procesando {i}/{total}: {contenido.get('titulo', 'Sin título')}")
                
                resultado = self.publicar_contenido(contenido)
                if resultado:
                    exitosos += 1
                
                # Evitar sobrecarga del servidor
                time.sleep(2)
            
            print(f"\nActualización completada: {exitosos}/{total} publicados exitosamente")
            self._registrar_log(f"Actualización masiva completada: {exitosos}/{total} exitosos")
            
        except Exception as e:
            self._registrar_log(f"Error en actualización masiva: {str(e)}", "ERROR")
            print(f"Error: {str(e)}")
    
    def sincronizar_documentos(self, directorio_documentos: str):
        """
        Sincroniza documentos desde un directorio local con la página web.
        
        Args:
            directorio_documentos (str): Ruta al directorio con documentos
        """
        extensiones_permitidas = ['.pdf', '.docx', '.xlsx', '.pptx']
        documentos_procesados = []
        
        for archivo in os.listdir(directorio_documentos):
            extension = os.path.splitext(archivo)[1].lower()
            
            if extension in extensiones_permitidas:
                ruta_completa = os.path.join(directorio_documentos, archivo)
                
                # Preparar metadatos del documento
                contenido = {
                    'titulo': os.path.splitext(archivo)[0].replace('_', ' ').title(),
                    'contenido': f'<p>Documento disponible para descarga: {archivo}</p>',
                    'categoria': 'documentos',
                    'autor': 'Departamento de Sistemas y Computación',
                    'archivo_adjunto': archivo,
                    'tamaño_archivo': os.path.getsize(ruta_completa)
                }
                
                resultado = self.publicar_contenido(contenido)
                if resultado:
                    documentos_procesados.append(archivo)
        
        print(f"Documentos sincronizados: {len(documentos_procesados)}")
        return documentos_procesados


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar actualizador
    actualizador = ActualizadorWebDepartamental(
        url_base="https://sistemas.itmexicali.edu.mx",
        api_key="API_KEY_EJEMPLO"
    )
    
    # Publicar contenido individual
    nuevo_contenido = {
        'titulo': 'Nuevo Sistema de Tickets Implementado',
        'contenido': '<p>Se ha implementado un nuevo sistema de tickets...</p>',
        'categoria': 'noticias',
        'autor': 'Admin Sistemas'
    }
    
    actualizador.publicar_contenido(nuevo_contenido)
    
    # Actualización masiva
    actualizador.actualizar_contenido_masivo('contenidos_julio_2025.json')