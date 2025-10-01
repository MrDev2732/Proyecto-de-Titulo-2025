"""
Servicio para integración con Google Maps API.

Proporciona funcionalidades para validar direcciones, obtener coordenadas
y verificar ubicaciones dentro de Chile.
"""

import asyncio
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote

import aiohttp

from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class GoogleMapsService:
    """Servicio para integración con Google Maps API."""

    # URL base de la API de Google Maps
    GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"

    @staticmethod
    async def validate_address_in_chile(address: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validar si una dirección existe y está ubicada en Chile.

        Args:
            address: Dirección a validar

        Returns:
            Tuple[bool, Dict]: (es_válida, información_detallada)
        """
        if not settings.google_maps.api_key or not settings.google_maps.enable_validation:
            logger.warning("Google Maps API key no configurada o validación deshabilitada, saltando validación de dirección")
            return True, {
                "status": "API_KEY_NOT_CONFIGURED",
                "message": "Validación de dirección no disponible",
                "address": address
            }

        try:
            # Preparar la consulta con restricción a Chile
            query_address = f"{address}, Chile"
            encoded_address = quote(query_address)

            # Construir URL con parámetros
            url = f"{GoogleMapsService.GEOCODING_API_URL}?address={encoded_address}&key={settings.google_maps.api_key}&region=cl&components=country:CL"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Error en Google Maps API: HTTP {response.status}")
                        return False, {
                            "status": "API_ERROR",
                            "message": "Error al conectar con Google Maps",
                            "address": address
                        }

                    data = await response.json()

                    # Procesar respuesta
                    return GoogleMapsService._process_geocoding_response(data, address)

        except asyncio.TimeoutError:
            logger.error("Timeout al validar dirección con Google Maps")
            return False, {
                "status": "TIMEOUT",
                "message": "Tiempo de espera agotado al validar dirección",
                "address": address
            }
        except Exception as e:
            logger.error(f"Error al validar dirección con Google Maps: {e}")
            return False, {
                "status": "ERROR",
                "message": f"Error interno: {str(e)}",
                "address": address
            }

    @staticmethod
    def _process_geocoding_response(data: Dict[str, Any], original_address: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Procesar respuesta de la API de Geocoding.

        Args:
            data: Respuesta JSON de Google Maps
            original_address: Dirección original consultada

        Returns:
            Tuple[bool, Dict]: (es_válida, información_detallada)
        """
        status = data.get("status", "UNKNOWN")

        if status == "OK" and data.get("results"):
            result = data["results"][0]  # Tomar el primer resultado

            # Extraer información relevante
            formatted_address = result.get("formatted_address", "")
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            address_components = result.get("address_components", [])

            # Verificar que esté en Chile
            is_in_chile = GoogleMapsService._is_address_in_chile(address_components)
            
            if not is_in_chile:
                return False, {
                    "status": "NOT_IN_CHILE",
                    "message": "La dirección no está ubicada en Chile",
                    "address": original_address,
                    "formatted_address": formatted_address
                }

            # Extraer información de la comuna y región
            locality_info = GoogleMapsService._extract_locality_info(address_components)

            return True, {
                "status": "VALID",
                "message": "Dirección válida en Chile",
                "address": original_address,
                "formatted_address": formatted_address,
                "coordinates": {
                    "lat": location.get("lat"),
                    "lng": location.get("lng")
                },
                "locality": locality_info.get("locality"),
                "administrative_area": locality_info.get("administrative_area"),
                "country": "Chile"
            }

        elif status == "ZERO_RESULTS":
            return False, {
                "status": "NOT_FOUND",
                "message": "No se encontró la dirección especificada",
                "address": original_address
            }
        elif status == "OVER_QUERY_LIMIT":
            logger.warning("Límite de consultas de Google Maps excedido")
            return True, {  # Permitir la dirección si hay límite de API
                "status": "QUERY_LIMIT_EXCEEDED",
                "message": "Límite de consultas excedido, dirección no validada",
                "address": original_address
            }
        elif status == "REQUEST_DENIED":
            logger.error("Solicitud denegada por Google Maps API")
            return False, {
                "status": "REQUEST_DENIED",
                "message": "Solicitud denegada por Google Maps",
                "address": original_address
            }
        else:
            return False, {
                "status": "INVALID",
                "message": f"Error en validación: {status}",
                "address": original_address
            }

    @staticmethod
    def _is_address_in_chile(address_components: list) -> bool:
        """
        Verificar si los componentes de dirección indican que está en Chile.

        Args:
            address_components: Componentes de dirección de Google Maps

        Returns:
            bool: True si está en Chile
        """
        for component in address_components:
            types = component.get("types", [])
            if "country" in types:
                short_name = component.get("short_name", "").upper()
                long_name = component.get("long_name", "").upper()
                return short_name == "CL" or "CHILE" in long_name

        return False

    @staticmethod
    def _extract_locality_info(address_components: list) -> Dict[str, Optional[str]]:
        """
        Extraer información de localidad (comuna/ciudad y región).

        Args:
            address_components: Componentes de dirección de Google Maps

        Returns:
            Dict con información de localidad
        """
        locality = None
        administrative_area = None

        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("long_name", "")

            # Comuna o ciudad
            if "locality" in types or "administrative_area_level_3" in types:
                locality = long_name
            # Región
            elif "administrative_area_level_1" in types:
                administrative_area = long_name

        return {
            "locality": locality,
            "administrative_area": administrative_area
        }

    @staticmethod
    async def get_address_suggestions(partial_address: str, limit: int = 5) -> list:
        """
        Obtener sugerencias de direcciones basadas en texto parcial.

        Args:
            partial_address: Texto parcial de dirección
            limit: Número máximo de sugerencias

        Returns:
            List de sugerencias de direcciones
        """
        if not settings.google_maps.api_key or not settings.google_maps.enable_validation:
            return []

        try:
            # Usar Places API para autocompletado
            query = f"{partial_address}, Chile"
            encoded_query = quote(query)

            url = f"{GoogleMapsService.PLACES_API_URL}?input={encoded_query}&inputtype=textquery&fields=formatted_address,geometry&key={settings.google_maps.api_key}&locationbias=country:cl"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("status") == "OK":
                            candidates = data.get("candidates", [])
                            suggestions = []

                            for candidate in candidates[:limit]:
                                suggestions.append({
                                    "address": candidate.get("formatted_address", ""),
                                    "coordinates": candidate.get("geometry", {}).get("location", {})
                                })

                            return suggestions

            return []

        except Exception as e:
            logger.error(f"Error obteniendo sugerencias de dirección: {e}")
            return []


# Función de conveniencia para validación rápida
async def validate_chilean_address(address: str) -> Tuple[bool, str]:
    """
    Función de conveniencia para validar dirección chilena.

    Args:
        address: Dirección a validar

    Returns:
        Tuple[bool, str]: (es_válida, mensaje)
    """
    is_valid, details = await GoogleMapsService.validate_address_in_chile(address)

    if is_valid:
        return True, details.get("message", "Dirección válida")
    else:
        return False, details.get("message", "Dirección inválida")
