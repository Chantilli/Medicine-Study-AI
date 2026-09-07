"""
Script de PRUEBA independiente para la API de ICD-11 de la OMS.

No es parte de la app — es solo para obtener una respuesta real de la
API y así poder construir icd11_terminologia.py contra la forma real
de los datos, no contra lo que la documentación dice (que puede estar
desactualizada). Bórralo cuando ya no lo necesites; no forma parte de
Medicine Study AI.

CÓMO CORRERLO (no necesitas terminal en HF, esto es aparte):

Opción A — Google Colab (más fácil si no tienes Python instalado):
  1. Ve a https://colab.research.google.com/ → "Nuevo notebook"
  2. Pega TODO este archivo en una celda
  3. Reemplaza CLIENT_ID y CLIENT_SECRET abajo con tus valores reales
  4. Dale ▶ (Run) — Colab ya trae 'requests' instalado, no necesitas
     instalar nada.

Opción B — tu computadora (si ya tienes Python):
  1. Guarda esto como test_icd11_api.py
  2. pip install requests   (si no lo tienes)
  3. Reemplaza CLIENT_ID y CLIENT_SECRET abajo
  4. python test_icd11_api.py

Al terminar, copia TODO lo que imprime la terminal/celda y pégamelo en
el chat — eso es lo que necesito para construir el módulo real.
"""
import requests

# ============================================================
# ✏️ SOLO TOCA ESTAS DOS LÍNEAS — nada más en todo el archivo.
# Reemplaza el texto entre comillas manteniendo las comillas.
# ============================================================
CLIENT_ID = "PEGA_AQUI_TU_CLIENT_ID"
CLIENT_SECRET = "PEGA_AQUI_TU_CLIENT_SECRET"
# ============================================================
# 🚫 NO TOQUES NADA DE AQUÍ PARA ABAJO. Estas dos URLs son fijas,
# son la dirección de la API de la OMS, no tus credenciales —
# no se reemplazan por nada que hayas copiado de icd.who.int.
# ============================================================
TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL = "https://id.who.int/icd/release/11/2024-01/mms/search"


def _validar_que_no_se_confundieron_las_variables():
    """Chequeo de seguridad: si CLIENT_ID/SECRET quedaron igual al
    placeholder, o si por error alguien pegó algo en TOKEN_URL/SEARCH_URL
    en vez de arriba, esto lo avisa ANTES de intentar conectar — en vez
    de un SyntaxError confuso al correr el script."""
    problemas = []
    if CLIENT_ID == "PEGA_AQUI_TU_CLIENT_ID":
        problemas.append("No reemplazaste CLIENT_ID todavía (línea con 'PEGA_AQUI_TU_CLIENT_ID').")
    if CLIENT_SECRET == "PEGA_AQUI_TU_CLIENT_SECRET":
        problemas.append("No reemplazaste CLIENT_SECRET todavía (línea con 'PEGA_AQUI_TU_CLIENT_SECRET').")
    if not TOKEN_URL.startswith("https://icdaccessmanagement.who.int"):
        problemas.append("¡TOKEN_URL fue modificado! Debe quedar exactamente como estaba — no lo toques.")
    if not SEARCH_URL.startswith("https://id.who.int"):
        problemas.append("¡SEARCH_URL fue modificado! Debe quedar exactamente como estaba — no lo toques.")
    return problemas


def paso_1_obtener_token():
    print("=" * 70)
    print("PASO 1 — Pidiendo el token de acceso...")
    print("=" * 70)

    # Intento A: credenciales como parámetros del formulario (lo más común).
    print("Intento A: credenciales en el cuerpo de la solicitud...")
    token = _intentar_token_form_params()
    if token:
        return token

    # Intento B: credenciales por HTTP Basic Auth — algunos servidores OAuth2
    # (incluida la OMS, según el caso) exigen este método en vez del anterior.
    # 'invalid_client' es exactamente el error típico cuando se usa el método
    # equivocado, así que vale la pena probar el otro automáticamente.
    print()
    print("Intento A falló. Intento B: credenciales por HTTP Basic Auth...")
    token = _intentar_token_basic_auth()
    return token


def _intentar_token_form_params():
    try:
        respuesta = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "icdapi_access",
            },
            timeout=15,
        )
    except Exception as ex:
        print(f"❌ No se pudo conectar: {ex}")
        return None
    return _procesar_respuesta_token(respuesta)


def _intentar_token_basic_auth():
    try:
        respuesta = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": "icdapi_access"},
            auth=(CLIENT_ID, CLIENT_SECRET),
            timeout=15,
        )
    except Exception as ex:
        print(f"❌ No se pudo conectar: {ex}")
        return None
    return _procesar_respuesta_token(respuesta)


def _procesar_respuesta_token(respuesta):
    print(f"Código de estado HTTP: {respuesta.status_code}")
    try:
        datos = respuesta.json()
    except Exception:
        print("❌ La respuesta no es JSON. Texto crudo:")
        print(respuesta.text[:1000])
        return None

    token = datos.get("access_token")
    datos_seguros_para_mostrar = {k: v for k, v in datos.items() if k != "access_token"}
    print("Campos de la respuesta (sin el token):")
    print(datos_seguros_para_mostrar)
    if token:
        print(f"✅ access_token recibido (longitud: {len(token)} caracteres)")
    else:
        print("❌ No vino 'access_token' en esta respuesta.")
    return token


def paso_2_buscar_termino(token, termino="diabetes"):
    print()
    print("=" * 70)
    print(f"PASO 2 — Buscando el término '{termino}'...")
    print("=" * 70)
    try:
        respuesta = requests.get(
            SEARCH_URL,
            params={"q": termino},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Accept-Language": "en",
                "API-Version": "v2",
            },
            timeout=15,
        )
    except Exception as ex:
        print(f"❌ No se pudo conectar: {ex}")
        return

    print(f"Código de estado HTTP: {respuesta.status_code}")
    try:
        datos = respuesta.json()
        print("Respuesta JSON completa (esto SÍ pégamelo completo, no es sensible):")
        print(datos)
    except Exception:
        print("❌ La respuesta no es JSON. Texto crudo:")
        print(respuesta.text[:2000])


if __name__ == "__main__":
    problemas = _validar_que_no_se_confundieron_las_variables()
    if problemas:
        print("⚠️  No se puede continuar todavía:")
        for p in problemas:
            print(f"   • {p}")
        print()
        print("Revisa: SOLO se editan CLIENT_ID y CLIENT_SECRET (arriba del todo).")
        print("TOKEN_URL y SEARCH_URL deben quedar exactamente como venían.")
    else:
        token = paso_1_obtener_token()
        if token:
            paso_2_buscar_termino(token, "diabetes")
        else:
            print()
            print("=" * 70)
            print("Ninguno de los dos métodos funcionó. Antes de seguir, revisa:")
            print("=" * 70)
            print("1. Que copiaste el Client Secret COMPLETO — a veces los cuadros de")
            print("   texto en el navegador cortan el final si es muy largo.")
            print("2. Que el Client Id y el Client Secret no quedaron al revés")
            print("   (que no pegaste uno en el lugar del otro).")
            print("3. Que las credenciales son específicamente de la API de ICD-11")
            print("   (https://icd.who.int/icdapi), no de otro servicio de la OMS.")
            print("4. Si acabas de crear las credenciales, espera 1-2 minutos —")
            print("   a veces tardan en activarse del lado de la OMS.")
            print()
            print("Pégame TODO lo que imprimió arriba (los dos intentos, A y B) y seguimos.")
