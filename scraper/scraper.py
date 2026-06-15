import requests
from bs4 import BeautifulSoup

_URL = "https://eltoque.com/tasas-de-cambio-cuba"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _get_price_by_flag(soup: BeautifulSoup, flag_class: str) -> float:
    """
    Obtiene el precio para una bandera específica.

    Args:
        flag_class: Clase de la bandera (ej: 'flag-icon-US')

    Returns:
        float: El precio extraído y convertido a float
    """
    # Buscar la bandera y subir al <tr> padre
    flag = soup.find("span", class_=flag_class)
    if not flag:
        raise RuntimeError(f"No se encontró la bandera {flag_class} en la página")

    row = flag.find_parent("tr")

    # El precio está en el span con clase text-lg dentro del <tr>
    # Formato del texto: "535.00\xa0CUP"
    price_span = row.find("span", class_="text-lg")
    if not price_span:
        raise RuntimeError(f"No se encontró el precio para {flag_class} en la fila")

    return float(price_span.get_text().replace("\xa0", " ").split()[0])


def get_rate() -> dict:
    """
    Devuelve la tasa informal CUP/USD desde eltoque.com.
    Retorna un dict con:
      - 'rate'  (float): CUP por 1 USD
      - 'change' (float): variacion diaria
    """
    response = requests.get(_URL, headers=_HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    usd = _get_price_by_flag(soup, "flag-icon-US")
    euro = _get_price_by_flag(soup, "flag-icon-EU")
    mlc = _get_price_by_flag(soup, "flag-icon-MLC")
    cad = _get_price_by_flag(soup, "flag-icon-CA")
    mxn = _get_price_by_flag(soup, "flag-icon-MX")
    zelle = _get_price_by_flag(soup, "flag-icon-ZELLE")
    cla = _get_price_by_flag(soup, "flag-icon-CLA")

    return {
        "usd": usd,
        "euro": euro,
        "mlc": mlc,
        "cad": cad,
        "mxn": mxn,
        "zelle": zelle,
        "cla": cla,
    }
