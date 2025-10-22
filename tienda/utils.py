# utils.py

# generar firma HMAC-SHA256 y formatear value para confirmation
import hmac
import hashlib
from decimal import Decimal

def _hmac_sha256_hex(secret: str, message: str) -> str:
    """
    Genera un hash HMAC-SHA256 en hexadecimal.
    """
    return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

import hashlib

def generate_payment_signature(api_key: str, merchant_id: str, reference_code: str, amount: str, currency: str, secret_key: str = None) -> str:
    """
    Genera la firma para el formulario WebCheckout de PayU (sandbox).
    Cadena base: ApiKey~merchantId~referenceCode~amount~currency
    Genera la firma para el formulario WebCheckout de PayU.
    Cadena base: apiKey~merchantId~referenceCode~amount~currency
    """
    base = f"{api_key}~{merchant_id}~{reference_code}~{amount}~{currency}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()
    secret = secret_key or api_key
    return _hmac_sha256_hex(secret, base)


def format_confirmation_value(value_str: str) -> str:
    """
    Da formato correcto al valor recibido en la confirmación de PayU.
    - Redondea a 1 decimal si el segundo decimal es 0.
    - Usa 2 decimales en otros casos.
    Ej: 150.20 -> "150.2", 150.00 -> "150.0", 150.25 -> "150.25"
    """
    # Convertimos a Decimal para precisión y redondeamos a 2 decimales
    val = Decimal(value_str).quantize(Decimal("0.01"))
    # Si el último dígito es '0', lo formateamos a 1 decimal. Si no, a 2.
    return f"{val:.1f}" if str(val)[-1] == '0' else f"{val:.2f}"

def generate_confirmation_signature(api_key: str, merchant_id: str, reference_sale: str, value: str, currency: str, state_pol: str, secret_key: str = None) -> str:
    """
    Genera la firma que debes comparar con la enviada por PayU en confirmation.
    Cadena base: apiKey~merchant_id~reference_sale~new_value~currency~state_pol
    """
    new_value = format_confirmation_value(value) # Usamos la función de formato
    base = f"{api_key}~{merchant_id}~{reference_sale}~{new_value}~{currency}~{state_pol}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()
