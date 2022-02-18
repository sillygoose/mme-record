import logging

from config.configuration import Configuration
from geocodio import GeocodioClient
from geocodio.exceptions import GeocodioAuthError, GeocodioDataError, GeocodioServerError, GeocodioError


_LOGGER = logging.getLogger('mme')


class Geocoding:

    _geocodio_client = None

def initialize_geocodio(config: Configuration):
    Geocoding._geocodio_client = None
    try:
        if config.geocodio.enable:
            Geocoding._geocodio_client = GeocodioClient(config.geocodio.api_key)
            _LOGGER.info(f"Using the geocod.io service for reverse geocoding of locations")
    except AttributeError:
        _LOGGER.error(f"YAML file error setting up geocod.io reverse geocoding")
        pass


def reverse_geocode(latitude: float, longitude: float) -> str:
    if Geocoding._geocodio_client:
        formatted_address = f"({latitude:.06f}, {longitude:.06f})"
        try:
            reversed = Geocoding._geocodio_client.reverse((latitude, longitude))
            components = Geocoding._geocodio_client.parse(reversed.formatted_address).get('address_components', None)
            if components:
                formatted_address = f"{components.get('formatted_street')}, {components.get('city')}, {components.get('state')}, {components.get('country')}"
        except (GeocodioAuthError, GeocodioDataError, GeocodioServerError, GeocodioError) as e:
            pass # _LOGGER.error(f"geocod.io reverse geocoding error: {e}")
        finally:
            return formatted_address
    else:
        return f"({latitude:.06f}, {longitude:.06f})"

def parse_address(address: str) -> dict:
    address_components = None
    if Geocoding._geocodio_client:
        try:
            address_components = Geocoding._geocodio_client.parse(address).get('address_components', None)
        except (GeocodioAuthError, GeocodioDataError, GeocodioServerError, GeocodioError) as e:
            _LOGGER.error(f"geocod.io parsing address error: {e}")
    return address_components
