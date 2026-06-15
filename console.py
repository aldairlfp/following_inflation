import os
import time

from scraper.scraper import get_rate


def clear_console():
    # 'nt' means Windows, 'posix' covers macOS and Linux
    os.system("cls" if os.name == "nt" else "clear")


if __name__ == "__main__":
    while True:
        try:
            rates = get_rate()
            clear_console()
            print("Tasas de cambio informales (CUP por unidad):")
            for currency, rate in rates.items():
                print(f"{currency.upper()}: {rate:.2f} CUP")
            time.sleep(60)  # Espera 60 segundos antes de actualizar
        except Exception as e:
            print(f"Error al obtener las tasas: {e}")
