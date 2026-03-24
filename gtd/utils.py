# SDS 4.7 — Bootstrap colour class to hex mapping for Chart.js
BOOTSTRAP_HEX: dict[str, str] = {
    'primary': '#0d6efd',
    'secondary': '#6c757d',
    'success': '#198754',
    'danger': '#dc3545',
    'warning': '#ffc107',
    'info': '#0dcaf0',
    'light': '#f8f9fa',
    'dark': '#212529',
}


def _bootstrap_to_hex(color_name: str) -> str:
    return BOOTSTRAP_HEX.get(color_name, '#6c757d')
