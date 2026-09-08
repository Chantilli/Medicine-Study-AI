"""
Calculadoras clínicas (Fase 5).

Funciones puras, deterministas, sin llamadas a IA ni a la base de datos:
IMC, superficie corporal, aclaramiento de creatinina / TFG estimada, y
un calculador genérico de dosis por peso corporal con techo de dosis
máxima. Se completa con una tabla de referencia (pequeña, curada a mano)
de ajuste de dosis por función renal para algunos fármacos comunes en
la práctica clínica — SIEMPRE con la advertencia de que es un punto de
partida educativo, no un sustituto de una fuente clínica actualizada
(ficha técnica, Micromedex, UpToDate, etc.) ni de la validación de un
médico o farmacéutico antes de aplicarse a un paciente real.

Todas las funciones son defensivas: con datos inválidos (peso <= 0,
altura <= 0, texto no numérico, etc.) devuelven un dict con "error" en
vez de lanzar excepción, para que la UI siempre tenga algo legible que
mostrar — mismo patrón defensivo que examenes.py / flashcards.py.
"""
import math
import unicodedata

from traducciones import t


def _a_float(valor):
    """Convierte a float de forma tolerante (acepta comas decimales, strings vacíos -> None)."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        return None
    return float(texto)


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni espacios extra — para comparar nombres de fármacos."""
    if not texto:
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))



def calcular_imc(peso_kg, altura_cm, idioma: str = "es") -> dict:
    """
    Índice de Masa Corporal = peso(kg) / altura(m)^2.
    Devuelve {"valor": float, "categoria": str} o {"error": str}.
    """
    try:
        peso_kg = _a_float(peso_kg)
        altura_cm = _a_float(altura_cm)
    except (TypeError, ValueError):
        return {"error": t("err_peso_altura_numeros", idioma)}
    if not peso_kg or not altura_cm or peso_kg <= 0 or altura_cm <= 0:
        return {"error": t("err_peso_altura_mayores_cero", idioma)}

    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m ** 2)

    if imc < 18.5:
        categoria = "Bajo peso"
    elif imc < 25:
        categoria = "Peso normal"
    elif imc < 30:
        categoria = "Sobrepeso"
    elif imc < 35:
        categoria = "Obesidad grado I"
    elif imc < 40:
        categoria = "Obesidad grado II"
    else:
        categoria = "Obesidad grado III"

    return {"valor": round(imc, 1), "categoria": categoria}



def calcular_superficie_corporal(peso_kg, altura_cm, formula: str = "mosteller", idioma: str = "es") -> dict:
    """
    Superficie corporal en m². 'formula' es 'mosteller' (la más usada
    hoy, más simple) o 'dubois' (la clásica, todavía citada para dosis
    oncológicas por m²).
    """
    try:
        peso_kg = _a_float(peso_kg)
        altura_cm = _a_float(altura_cm)
    except (TypeError, ValueError):
        return {"error": t("err_peso_altura_numeros", idioma)}
    if not peso_kg or not altura_cm or peso_kg <= 0 or altura_cm <= 0:
        return {"error": t("err_peso_altura_mayores_cero", idioma)}

    if formula == "dubois":
        bsa = 0.007184 * (peso_kg ** 0.425) * (altura_cm ** 0.725)
        nombre_formula = "Du Bois & Du Bois"
    else:
        bsa = math.sqrt((altura_cm * peso_kg) / 3600)
        nombre_formula = "Mosteller"

    return {"valor": round(bsa, 2), "formula": nombre_formula}



def calcular_peso_ajustado(peso_kg: float, altura_cm: float, sexo: str) -> float:
    """
    Peso ajustado para pacientes con obesidad significativa: Cockcroft-
    Gault sobreestima el aclaramiento si se usa el peso real cuando este
    supera ~30% del peso ideal. Peso ideal por la fórmula de Devine;
    peso ajustado = ideal + 0.4*(real - ideal).
    """
    altura_pulgadas = altura_cm / 2.54
    pulgadas_sobre_5_pies = max(altura_pulgadas - 60, 0)
    base = 50.0 if sexo == "M" else 45.5
    peso_ideal = base + 2.3 * pulgadas_sobre_5_pies
    if peso_kg <= peso_ideal * 1.3:
        return peso_kg
    return peso_ideal + 0.4 * (peso_kg - peso_ideal)


def calcular_aclaramiento_creatinina(edad, peso_kg, creatinina_mg_dl, sexo,
                                       altura_cm=None, usar_peso_ajustado: bool = False,
                                       idioma: str = "es") -> dict:
    """
    Cockcroft-Gault. Es la fórmula que se sigue usando en la práctica
    para AJUSTAR DOSIS de fármacos (a diferencia de CKD-EPI, pensada
    para estadificar enfermedad renal crónica, no para dosificación).

    sexo: "M" o "F". Si usar_peso_ajustado=True y se da altura_cm, usa
    peso ajustado en vez del peso real (recomendado con obesidad
    significativa).
    """
    try:
        edad_f = _a_float(edad)
        peso_kg_f = _a_float(peso_kg)
        creatinina_f = _a_float(creatinina_mg_dl)
    except (TypeError, ValueError):
        return {"error": t("err_edad_peso_creatinina_numeros", idioma)}
    if not edad_f or not peso_kg_f or not creatinina_f or edad_f <= 0 or peso_kg_f <= 0 or creatinina_f <= 0:
        return {"error": t("err_edad_peso_creatinina_mayores_cero", idioma)}
    sexo = (sexo or "").strip().upper()[:1]
    if sexo not in ("M", "F"):
        return {"error": t("err_sexo_m_f", idioma)}

    peso_usado = peso_kg_f
    nota_peso = ""
    if usar_peso_ajustado and altura_cm:
        try:
            altura_f = _a_float(altura_cm)
            if altura_f:
                peso_usado = calcular_peso_ajustado(peso_kg_f, altura_f, sexo)
                if abs(peso_usado - peso_kg_f) > 0.1:
                    nota_peso = t("nota_peso_ajustado", idioma, valor=f"{peso_usado:.1f}")
        except (TypeError, ValueError):
            pass

    crcl = ((140 - edad_f) * peso_usado) / (72 * creatinina_f)
    if sexo == "F":
        crcl *= 0.85
    crcl = max(crcl, 0.0)

    if crcl >= 90:
        categoria = "Función renal normal"
    elif crcl >= 60:
        categoria = "Insuficiencia renal leve"
    elif crcl >= 30:
        categoria = "Insuficiencia renal moderada"
    elif crcl >= 15:
        categoria = "Insuficiencia renal grave"
    else:
        categoria = "Fallo renal"

    return {
        "valor_ml_min": round(crcl, 1),
        "categoria": categoria,
        "formula": "Cockcroft-Gault",
        "nota": nota_peso,
    }


def calcular_egfr_ckd_epi(edad, creatinina_mg_dl, sexo, idioma: str = "es") -> dict:
    """
    CKD-EPI 2021 (versión sin coeficiente racial). Estima la TFG en
    mL/min/1.73m² — se usa para ESTADIFICAR enfermedad renal crónica,
    no está pensada para ajustar dosis de fármacos (para eso usa
    calcular_aclaramiento_creatinina / Cockcroft-Gault).
    """
    try:
        edad_f = _a_float(edad)
        creatinina_f = _a_float(creatinina_mg_dl)
    except (TypeError, ValueError):
        return {"error": t("err_edad_creatinina_numeros", idioma)}
    if not edad_f or not creatinina_f or edad_f <= 0 or creatinina_f <= 0:
        return {"error": t("err_edad_creatinina_mayores_cero", idioma)}
    sexo = (sexo or "").strip().upper()[:1]
    if sexo not in ("M", "F"):
        return {"error": t("err_sexo_m_f", idioma)}

    if sexo == "F":
        kappa, alfa, factor_sexo = 0.7, -0.241, 1.012
    else:
        kappa, alfa, factor_sexo = 0.9, -0.302, 1.0

    ratio = creatinina_f / kappa
    exponente = alfa if ratio <= 1 else -1.200
    egfr = 142 * (ratio ** exponente) * (0.9938 ** edad_f) * factor_sexo

    if egfr >= 90:
        etapa = "G1 (normal o alta)"
    elif egfr >= 60:
        etapa = "G2 (levemente disminuida)"
    elif egfr >= 45:
        etapa = "G3a (leve a moderadamente disminuida)"
    elif egfr >= 30:
        etapa = "G3b (moderada a gravemente disminuida)"
    elif egfr >= 15:
        etapa = "G4 (gravemente disminuida)"
    else:
        etapa = "G5 (fallo renal)"

    return {"valor_ml_min_173": round(egfr, 1), "etapa": etapa, "formula": "CKD-EPI 2021"}



def calcular_dosis_por_peso(peso_kg, mg_por_kg, dosis_max_mg=None,
                              dosis_min_mg=None, tomas_por_dia=None, idioma: str = "es") -> dict:
    """
    Calcula dosis_total = peso_kg * mg_por_kg, respetando techo/piso si
    se dan (dosis_max_mg / dosis_min_mg — común en pediatría, donde la
    dosis por kg no debe superar la dosis de adulto). Si se da
    tomas_por_dia, también devuelve la dosis por toma.
    """
    try:
        peso_kg_f = _a_float(peso_kg)
        mg_por_kg_f = _a_float(mg_por_kg)
    except (TypeError, ValueError):
        return {"error": t("err_peso_dosiskg_numeros", idioma)}
    if not peso_kg_f or not mg_por_kg_f or peso_kg_f <= 0 or mg_por_kg_f <= 0:
        return {"error": t("err_peso_dosiskg_mayores_cero", idioma)}

    dosis_total = peso_kg_f * mg_por_kg_f
    techo_aplicado = False
    try:
        dosis_max_f = _a_float(dosis_max_mg)
        if dosis_max_f and dosis_max_f > 0 and dosis_total > dosis_max_f:
            dosis_total = dosis_max_f
            techo_aplicado = True
    except (TypeError, ValueError):
        pass

    piso_aplicado = False
    try:
        dosis_min_f = _a_float(dosis_min_mg)
        if dosis_min_f and dosis_min_f > 0 and dosis_total < dosis_min_f:
            dosis_total = dosis_min_f
            piso_aplicado = True
    except (TypeError, ValueError):
        pass

    resultado = {
        "dosis_total_mg": round(dosis_total, 1),
        "techo_aplicado": techo_aplicado,
        "piso_aplicado": piso_aplicado,
    }

    try:
        tomas_f = _a_float(tomas_por_dia)
        if tomas_f and tomas_f > 0:
            tomas_int = int(round(tomas_f))
            resultado["dosis_por_toma_mg"] = round(dosis_total / tomas_int, 1)
            resultado["tomas_por_dia"] = tomas_int
    except (TypeError, ValueError):
        pass

    return resultado



AJUSTES_RENALES_COMUNES = {
    "vancomicina": [
        (50, float("inf"), "15-20 mg/kg cada 8-12 h (ajustar por niveles séricos)"),
        (30, 50, "15-20 mg/kg cada 12-24 h (ajustar por niveles séricos)"),
        (10, 30, "15-20 mg/kg cada 24-48 h (ajustar por niveles séricos)"),
        (0, 10, "Dosis de carga y luego por niveles séricos; considerar diálisis"),
    ],
    "gentamicina": [
        (60, float("inf"), "Dosis estándar cada 8 h"),
        (40, 60, "Dosis estándar cada 12 h"),
        (20, 40, "Dosis estándar cada 24 h"),
        (0, 20, "Dosis estándar cada 48 h o por niveles séricos"),
    ],
    "metformina": [
        (45, float("inf"), "Dosis estándar"),
        (30, 45, "Reducir a la mitad; reevaluar riesgo/beneficio"),
        (0, 30, "Contraindicada (riesgo de acidosis láctica)"),
    ],
    "ciprofloxacino": [
        (50, float("inf"), "Dosis estándar (ej. 500 mg c/12 h)"),
        (30, 50, "250-500 mg cada 12 h"),
        (5, 30, "250-500 mg cada 18 h"),
        (0, 5, "250-500 mg cada 24 h (post-diálisis en días de diálisis)"),
    ],
    "enoxaparina": [
        (30, float("inf"), "Dosis estándar (ej. 1 mg/kg c/12 h)"),
        (0, 30, "Reducir a 1 mg/kg cada 24 h"),
    ],
    "digoxina": [
        (50, float("inf"), "Dosis estándar"),
        (10, 50, "Reducir dosis 25-75% y/o alargar intervalo; monitorizar niveles"),
        (0, 10, "Reducir dosis 75-90%; monitorizar niveles estrechamente"),
    ],
    "alopurinol": [
        (60, float("inf"), "Dosis estándar (hasta 300 mg/día)"),
        (30, 60, "Máximo ~200 mg/día"),
        (10, 30, "Máximo ~100 mg/día"),
        (0, 10, "100 mg cada 48-72 h"),
    ],
}


def obtener_ajuste_renal(farmaco: str, aclaramiento_ml_min, idioma: str = "es") -> dict:
    """
    Busca el fármaco (insensible a mayúsculas/acentos) en
    AJUSTES_RENALES_COMUNES y devuelve la banda que aplica al
    aclaramiento dado. Si el fármaco no está en la tabla, devuelve
    {"encontrado": False} para que la UI lo indique con claridad en vez
    de fallar o inventar un ajuste.

    NOTA sobre idioma: solo se traducen los mensajes de la UI (errores,
    "no encontrado"). El texto de 'instruccion' (ej. "15-20 mg/kg cada
    8-12 h") se deja SIEMPRE en español a propósito — es texto clínico
    de dosificación, y traducirlo automáticamente sin revisión médica es
    un riesgo real de introducir un error de dosis (el mismo tipo de
    problema que las traducciones automáticas de terminología clínica
    pueden causar). Mejor mostrarlo en español siempre que confiar en
    una traducción no verificada de una instrucción de dosis.
    """
    try:
        crcl = _a_float(aclaramiento_ml_min)
    except (TypeError, ValueError):
        return {"error": t("err_aclaramiento_numero", idioma)}
    if crcl is None:
        return {"error": t("err_falta_aclaramiento", idioma)}
    if not farmaco or not farmaco.strip():
        return {"error": t("err_escribe_farmaco", idioma)}

    clave = _normalizar(farmaco)
    bandas = AJUSTES_RENALES_COMUNES.get(clave)
    if not bandas:
        return {
            "encontrado": False,
            "mensaje": t("ajuste_no_encontrado", idioma, farmaco=farmaco),
        }

    for crcl_min, crcl_max, instruccion in bandas:
        if crcl_min <= crcl < crcl_max:
            techo = "∞" if crcl_max == float("inf") else crcl_max
            return {
                "encontrado": True,
                "farmaco": farmaco,
                "banda": f"CrCl {crcl_min}-{techo} mL/min",
                "instruccion": instruccion,
            }
    return {"encontrado": False, "mensaje": t("ajuste_sin_banda", idioma)}
