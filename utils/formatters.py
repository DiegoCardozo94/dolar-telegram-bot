
def emoji(diff):
    """
    Devuelve un emoji basado en la diferencia (diff) de la cotización.
    🟢 si sube, 🔴 si baja, 🟡 si se mantiene.
    """
    return "🟢" if diff > 0 else "🔴" if diff < 0 else "🟡"