
def emoji(diff):
    """
    Devuelve un emoji basado en la diferencia (diff) de la cotización.
    🟢 si sube, 🔴 si baja, 🟡 si se mantiene.
    """
    return "🟢" if diff > 0 else "🔴" if diff < 0 else "🟡"

def prepare_data(data_dict, initial_dict=None):
    """
    Prepara y formatea los datos de cotización para el renderizado HTML,
    incluyendo la comparación con las tasas de apertura.
    """
    prepared = {}
    for name, rates in data_dict.items():
        compra = float(rates.get("compra", rates)) if isinstance(rates, dict) else float(rates)
        venta = float(rates.get("venta", rates)) if isinstance(rates, dict) else float(rates)

        # 🔹 Apertura segura: si no existe, toma el valor actual
        apertura_compra = float(initial_dict.get(name, {}).get("compra", compra)) if initial_dict else compra
        apertura_venta = float(initial_dict.get(name, {}).get("venta", venta)) if initial_dict else venta

        diff_compra = compra - apertura_compra
        diff_venta = venta - apertura_venta
        pct_compra = f"{(diff_compra / apertura_compra * 100):+.2f}%" if apertura_compra else "+0.00%"
        pct_venta = f"{(diff_venta / apertura_venta * 100):+.2f}%" if apertura_venta else "+0.00%"

        # Usamos la función emoji de este mismo módulo
        emoji_compra = emoji(diff_compra)
        emoji_venta = emoji(diff_venta)

        prepared[name] = {
            "compra": f"{compra:.2f}",
            "venta": f"{venta:.2f}",
            "apertura_compra": f"{apertura_compra:.2f}",
            "apertura_venta": f"{apertura_venta:.2f}",
            "apertura_emoji_compra": emoji_compra,
            "apertura_emoji_venta": emoji_venta,
            "emoji_compra": emoji_compra,
            "emoji_venta": emoji_venta,
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        }

    return prepared