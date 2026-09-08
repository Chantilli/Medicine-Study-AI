"""
Clasificador de riesgo clínico (Fase 6 — seguridad clínica).

Medicine Study AI es una herramienta EDUCATIVA, no un servicio de
consejo médico ni de manejo de emergencias. Este módulo es un router
basado en reglas (regex sobre texto normalizado, no un modelo de ML)
que clasifica cada mensaje del estudiante en una de tres categorías
ANTES de que llegue al flujo normal del chat:

  "emergencia"      -> señales de una posible urgencia médica o de
                        salud mental EN CURSO. Se corta el flujo:
                        NO se le pasa al LLM, se muestra de inmediato
                        un mensaje con recursos de emergencia reales.
  "riesgo_personal"  -> suena a que el estudiante pregunta por SU
                        propia salud/tratamiento (no un caso de
                        estudio). No se bloquea, pero se le agrega un
                        aviso visible y un recordatorio reforzado al
                        contexto que se le manda al modelo.
  "educativo"        -> todo lo demás; sigue el flujo normal.

Es deliberadamente conservador con los patrones de "emergencia": exige
la combinación de un pronombre en primera persona ("tengo", "me",
"estoy"...) MUY cerca de una señal de alarma aguda, para no bloquear
preguntas de estudio legítimas en tercera persona ("¿qué causa el
dolor torácico?", "un paciente de 60 años presenta..."). No es
perfecto — ningún filtro basado en reglas lo es — por eso NUNCA es la
única capa: el SYSTEM_PROMPT en config.py también le recuerda al
modelo que esto es educativo, no consejo médico real.

Los patrones cubren los 5 idiomas de la app (es/en/fr/de/zh) — antes
solo reconocían español, lo cual era un vacío de seguridad real: un
estudiante describiendo una emergencia en inglés, francés, alemán o
chino simplemente no activaba el detector. La detección NO depende del
idioma seleccionado en la UI — revisa TODOS los idiomas a la vez sobre
el texto que escribió el estudiante, igual que el detector de
negación-contradictoria en citas_evidencia.py.
"""
import re
import unicodedata


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


_YO_ES = r"\b(yo|me|mi|mis|estoy|tengo|siento|padezco|sufro|no\s+puedo)\b"
_YO_EN = r"\b(i|i'?m|i\s+am|my|i\s+have|i\s+feel|i\s+can'?t|i\s+cannot)\b"
_YO_FR = r"\b(je|j'ai|je\s+suis|mon|ma|mes|je\s+ne\s+peux\s+pas|je\s+n'arrive\s+pas)\b"
_YO_DE = r"\b(ich|ich\s+habe|ich\s+bin|mein|meine|ich\s+kann\s+nicht|ich\s+fuhle|ich\s+fühle)\b"
# Chino: sin espacios entre palabras, así que no se usa \b/\s+ — basta con
# que 我 (yo) o 我的 (mi/mío) aparezca cerca del síntoma.
_YO_ZH = r"(我的|我)"

# --- Emergencia médica aguda: síntoma agudo + framing en primera persona ---
PATRONES_EMERGENCIA_MEDICA = [
    # Español
    ("dolor_toracico_agudo_es", rf"{_YO_ES}.{{0,40}}(dolor\s+(en\s+el\s+|de\s+)?pecho|dolor\s+toracico).{{0,60}}"
                                  rf"(no\s+puedo\s+respirar|falta\s+de\s+aire|sudo|brazo\s+izquierdo|mareo)"),
    ("dificultad_respiratoria_aguda_es", rf"{_YO_ES}.{{0,30}}(no\s+puedo\s+respirar|me\s+estoy\s+ahogando|"
                                          rf"falta\s+de\s+aire\s+(severa|grave|intensa))"),
    ("sangrado_severo_es", rf"{_YO_ES}.{{0,30}}(sangrado\s+(abundante|que\s+no\s+para)|no\s+deja\s+de\s+sangrar|hemorragia)"),
    ("sobredosis_actual_es", r"(me\s+tome|tome)\s+(todas\s+las\s+pastillas|una\s+sobredosis|"
                               r"demasiad[ao]s?\s+(pastillas|medicamento))"),
    ("convulsion_actual_es", rf"{_YO_ES}.{{0,30}}(estoy\s+convulsionando|convulsionando\s+ahora)"),
    ("perdida_conciencia_actual_es", r"(se\s+desmayo|perdio\s+el\s+conocimiento|no\s+responde|no\s+reacciona)"
                                       r".{0,30}(ahora|en\s+este\s+momento|justo\s+ahora)"),
    ("reaccion_alergica_grave_es", rf"{_YO_ES}.{{0,30}}(se\s+me\s+cerro\s+la\s+garganta|no\s+puedo\s+tragar|"
                                    rf"me\s+esta\s+hinchando\s+la\s+cara)"),
    # English
    ("dolor_toracico_agudo_en", rf"{_YO_EN}.{{0,40}}(chest\s+pain).{{0,60}}"
                                  rf"(can'?t\s+breathe|short(ness)?\s+of\s+breath|sweating|left\s+arm|dizzy)"),
    ("dificultad_respiratoria_aguda_en", rf"{_YO_EN}.{{0,30}}(can'?t\s+breathe|choking|"
                                          rf"severe\s+(shortness\s+of\s+breath|breathing\s+difficulty))"),
    ("sangrado_severo_en", rf"{_YO_EN}.{{0,30}}(heavy\s+bleeding|bleeding\s+(a\s+lot|won'?t\s+stop)|hemorrhag(e|ing))"),
    ("sobredosis_actual_en", r"(i\s+took|took)\s+(all\s+(the|my)\s+pills|an\s+overdose|too\s+many\s+(pills|medication))"),
    ("convulsion_actual_en", rf"{_YO_EN}.{{0,30}}(having\s+a\s+seizure|seizing\s+right\s+now|convulsing\s+now)"),
    ("perdida_conciencia_actual_en", r"(passed\s+out|lost\s+consciousness|not\s+responding|unresponsive)"
                                       r".{0,30}(right\s+now|just\s+now)"),
    ("reaccion_alergica_grave_en", rf"{_YO_EN}.{{0,30}}(throat\s+(is\s+)?closing|can'?t\s+swallow|"
                                    rf"face\s+(is\s+)?swelling)"),
    # Français
    ("dolor_toracico_agudo_fr", rf"{_YO_FR}.{{0,40}}(douleur\s+(a\s+la\s+|dans\s+la\s+)?poitrine|douleur\s+thoracique)"
                                  rf".{{0,60}}(n'arrive\s+pas\s+a\s+respirer|essoufflement|transpire|bras\s+gauche|vertige)"),
    ("dificultad_respiratoria_aguda_fr", rf"{_YO_FR}.{{0,30}}(n'arrive\s+pas\s+a\s+respirer|je\s+m'etouffe|"
                                          rf"essoufflement\s+(severe|grave|intense))"),
    ("sangrado_severo_fr", rf"{_YO_FR}.{{0,30}}(saignement\s+(abondant|qui\s+ne\s+s'arrete\s+pas)|hemorragie)"),
    ("sobredosis_actual_fr", r"(j'ai\s+pris|pris)\s+(tous\s+les\s+comprimes|une\s+overdose|"
                               r"trop\s+de\s+(comprimes|medicaments))"),
    ("convulsion_actual_fr", rf"{_YO_FR}.{{0,30}}(en\s+train\s+de\s+convulser|convulsions?\s+maintenant)"),
    ("perdida_conciencia_actual_fr", r"(s'est\s+evanoui|a\s+perdu\s+connaissance|ne\s+repond\s+pas|inconscient)"
                                       r".{0,30}(maintenant|a\s+l'instant)"),
    ("reaccion_alergica_grave_fr", rf"{_YO_FR}.{{0,30}}(gorge\s+se\s+ferme|n'arrive\s+pas\s+a\s+avaler|"
                                    rf"visage\s+(qui\s+)?gonfle)"),
    # Deutsch
    ("dolor_toracico_agudo_de", rf"{_YO_DE}.{{0,40}}(brustschmerzen|schmerzen\s+in\s+der\s+brust)"
                                  rf".{{0,60}}(kann\s+nicht\s+atmen|atemnot|schwitze|linker\s+arm|schwindel)"),
    ("dificultad_respiratoria_aguda_de", rf"{_YO_DE}.{{0,30}}(kann\s+nicht\s+atmen|ich\s+ersticke|"
                                          rf"schwere\s+atemnot)"),
    ("sangrado_severo_de", rf"{_YO_DE}.{{0,30}}(starke\s+blutung|blutung\s+hort\s+nicht\s+auf|blutet\s+stark)"),
    ("sobredosis_actual_de", r"(ich\s+habe|habe)\s+(alle\s+tabletten\s+genommen|eine\s+uberdosis\s+genommen|"
                               r"zu\s+viele\s+(tabletten|medikamente)\s+genommen)"),
    ("convulsion_actual_de", rf"{_YO_DE}.{{0,30}}(habe\s+gerade\s+einen\s+krampfanfall|krampft\s+jetzt)"),
    ("perdida_conciencia_actual_de", r"(ist\s+ohnmachtig\s+geworden|hat\s+das\s+bewusstsein\s+verloren|"
                                       r"reagiert\s+nicht).{0,30}(jetzt|gerade)"),
    ("reaccion_alergica_grave_de", rf"{_YO_DE}.{{0,30}}(hals\s+schnurt\s+zu|kann\s+nicht\s+schlucken|"
                                    rf"gesicht\s+schwillt\s+an)"),
    # 中文（简体）
    ("dolor_toracico_agudo_zh", rf"{_YO_ZH}.{{0,20}}(胸痛|胸部疼痛).{{0,30}}(无法呼吸|呼吸困难|出汗|左臂|头晕)"),
    ("dificultad_respiratoria_aguda_zh", rf"{_YO_ZH}.{{0,15}}(无法呼吸|喘不过气|呼吸(非常)?困难)"),
    ("sangrado_severo_zh", rf"{_YO_ZH}.{{0,15}}(大量出血|流血不止|出血严重)"),
    ("sobredosis_actual_zh", r"(我吃了|吃了).{0,15}(所有的?药|过量的?药|太多药)"),
    ("convulsion_actual_zh", rf"{_YO_ZH}.{{0,15}}(正在抽搐|现在抽搐)"),
    ("perdida_conciencia_actual_zh", r"(晕倒了|失去意识|没有反应|不省人事).{0,20}(现在|刚刚)"),
    ("reaccion_alergica_grave_zh", rf"{_YO_ZH}.{{0,15}}(喉咙.{{0,5}}肿|无法吞咽|脸.{{0,5}}肿)"),
]

# --- Autolesión / crisis de salud mental EN CURSO ---
PATRONES_EMERGENCIA_SALUD_MENTAL = [
    # Español
    ("ideacion_suicida_es", r"(quiero|voy\s+a|pienso\s+en|estoy\s+pensando\s+en)\s+"
                              r"(matarme|suicidarme|quitarme\s+la\s+vida)"),
    ("no_quiero_vivir_es", r"no\s+quiero\s+(seguir\s+vivi[ae]ndo|vivir\s+mas|existir\s+mas)"),
    ("autolesion_actual_es", r"(me\s+estoy\s+cortando|me\s+quiero\s+hacer\s+dano|"
                               r"me\s+lastime\s+a\s+proposito|me\s+voy\s+a\s+lastimar)"),
    # English
    ("ideacion_suicida_en", r"(i\s+want\s+to|i'?m\s+going\s+to|i'?m\s+thinking\s+about)\s+"
                              r"(kill\s+myself|end\s+my\s+life|commit\s+suicide)"),
    ("no_quiero_vivir_en", r"(i\s+don'?t\s+want\s+to\s+live|i\s+don'?t\s+want\s+to\s+keep\s+living|"
                             r"i\s+don'?t\s+want\s+to\s+exist)"),
    ("autolesion_actual_en", r"(i'?m\s+cutting\s+myself|i\s+want\s+to\s+hurt\s+myself|"
                               r"i'?m\s+going\s+to\s+hurt\s+myself|i\s+hurt\s+myself\s+on\s+purpose)"),
    # Français
    ("ideacion_suicida_fr", r"(je\s+veux|je\s+vais|je\s+pense\s+a)\s+"
                              r"(me\s+tuer|me\s+suicider|mettre\s+fin\s+a\s+mes\s+jours)"),
    ("no_quiero_vivir_fr", r"je\s+ne\s+veux\s+plus\s+(vivre|continuer\s+a\s+vivre|exister)"),
    ("autolesion_actual_fr", r"(je\s+suis\s+en\s+train\s+de\s+me\s+couper|je\s+veux\s+me\s+faire\s+du\s+mal|"
                               r"je\s+vais\s+me\s+faire\s+du\s+mal)"),
    # Deutsch
    ("ideacion_suicida_de", r"(ich\s+will|ich\s+werde)\s+(mich\s+umbringen|mich\s+toten|selbstmord\s+begehen)"),
    ("ideacion_suicida_de_zu", r"ich\s+denke\s+daran,?\s+(mich\s+umzubringen|mich\s+zu\s+toten|selbstmord\s+zu\s+begehen)"),
    ("no_quiero_vivir_de", r"ich\s+will\s+nicht\s+mehr\s+(leben|weiterleben|existieren)"),
    ("autolesion_actual_de", r"(ich\s+schneide\s+mich\s+gerade|ich\s+will\s+mir\s+selbst\s+schaden|"
                               r"ich\s+werde\s+mir\s+selbst\s+schaden)"),
    # 中文（简体）
    ("ideacion_suicida_zh", r"(我想|我要|我在想).{0,5}(自杀|结束自己的生命|杀死自己)"),
    ("no_quiero_vivir_zh", r"我不想.{0,10}(活了|再活下去|继续活着)"),
    ("autolesion_actual_zh", r"(我在割自己|我想伤害自己|我要伤害自己|我故意伤害自己)"),
]

# --- Consejo médico personal (no urgente, pero personal — no un caso de estudio) ---
PATRONES_RIESGO_PERSONAL = [
    # Español
    ("sintoma_personal_diagnostico_es", rf"{_YO_ES}.{{0,40}}(que\s+tengo|es\s+grave|deberia\s+preocuparme|"
                                          rf"es\s+normal\s+que\s+me)"),
    ("dosis_personal_es", r"(mi\s+dosis|mi\s+medicamento|estoy\s+tomando).{0,60}"
                            r"(deberia|puedo).{0,20}(aumentar|disminuir|dejar|cambiar|tomar)"),
    ("interaccion_personal_es", r"(yo\s+tomo|estoy\s+tomando|mi\s+medico\s+me\s+receto).{0,60}"
                                  r"(puedo\s+tomar|es\s+seguro\s+tomar|puedo\s+combinar)"),
    ("pregunta_dosis_directa_personal_es", rf"{_YO_ES}.{{0,30}}cuanto\s+(debo|puedo)\s+tomar"),
    ("autodiagnostico_directo_es", rf"{_YO_ES}.{{0,20}}(estos\s+sintomas|estas\s+molestias).{{0,30}}"
                                    rf"(que\s+podria\s+ser|que\s+enfermedad)"),
    # English
    ("sintoma_personal_diagnostico_en", rf"{_YO_EN}.{{0,40}}(what\s+do\s+i\s+have|is\s+this\s+serious|"
                                          rf"should\s+i\s+be\s+worried)"),
    ("dosis_personal_en", r"(my\s+dose|my\s+medication|i'?m\s+taking).{0,60}"
                            r"(should\s+i|can\s+i).{0,20}(increase|decrease|stop|change|take)"),
    ("interaccion_personal_en", r"(i\s+take|i\s+am\s+taking|i'?m\s+taking|my\s+doctor\s+prescribed).{0,60}"
                                  r"(can\s+i\s+take|is\s+it\s+safe\s+to\s+take|can\s+i\s+combine)"),
    ("pregunta_dosis_directa_personal_en", rf"{_YO_EN}.{{0,30}}how\s+much\s+(should|can)\s+i\s+take"),
    ("autodiagnostico_directo_en", rf"{_YO_EN}.{{0,20}}(these\s+symptoms|this\s+discomfort).{{0,30}}"
                                    rf"(what\s+could\s+(this|it)\s+be|what\s+(disease|condition))"),
    # Français
    ("sintoma_personal_diagnostico_fr", rf"{_YO_FR}.{{0,40}}(qu'est[- ]ce\s+que\s+j'ai|est[- ]ce\s+grave|"
                                          rf"devrais[- ]je\s+m'inquieter)"),
    ("dosis_personal_fr", r"(ma\s+dose|mon\s+medicament|je\s+prends).{0,60}"
                            r"(devrais[- ]je|puis[- ]je).{0,20}(augmenter|diminuer|arreter|changer|prendre)"),
    ("interaccion_personal_fr", r"(je\s+prends|mon\s+medecin\s+m'a\s+prescrit).{0,60}"
                                  r"(puis[- ]je\s+prendre|est[- ]ce\s+sur\s+de\s+prendre|puis[- ]je\s+combiner)"),
    ("pregunta_dosis_directa_personal_fr", rf"{_YO_FR}.{{0,30}}combien\s+(dois|puis)[- ]je\s+prendre"),
    ("autodiagnostico_directo_fr", rf"{_YO_FR}.{{0,20}}(ces\s+symptomes|ce\s+malaise).{{0,30}}"
                                    rf"(qu'est[- ]ce\s+que\s+ca\s+pourrait\s+etre|quelle\s+maladie)"),
    # Deutsch
    ("sintoma_personal_diagnostico_de", rf"{_YO_DE}.{{0,40}}(was\s+habe\s+ich|ist\s+das\s+ernst|"
                                          rf"sollte\s+ich\s+mir\s+sorgen\s+machen)"),
    ("dosis_personal_de", r"(meine\s+dosis|mein\s+medikament|ich\s+nehme).{0,60}"
                            r"(sollte\s+ich|kann\s+ich).{0,20}(erhohen|verringern|absetzen|andern|nehmen)"),
    ("interaccion_personal_de", r"(ich\s+nehme|mein\s+arzt\s+hat\s+mir\s+verschrieben).{0,60}"
                                  r"(kann\s+ich\s+nehmen|ist\s+es\s+sicher\s+zu\s+nehmen|kann\s+ich\s+kombinieren)"),
    ("pregunta_dosis_directa_personal_de", rf"{_YO_DE}.{{0,30}}wie\s+viel\s+(sollte|kann)\s+ich\s+nehmen"),
    ("autodiagnostico_directo_de", rf"{_YO_DE}.{{0,20}}(diese\s+symptome|diese\s+beschwerden).{{0,30}}"
                                    rf"(was\s+konnte\s+das\s+sein|welche\s+krankheit)"),
    # 中文（简体）
    ("sintoma_personal_diagnostico_zh", rf"{_YO_ZH}.{{0,15}}(得了什么病|严重吗|应该担心吗)"),
    ("dosis_personal_zh", r"(我的剂量|我的药|我在吃).{0,20}(应该|可以).{0,10}(增加|减少|停止|更换|吃)"),
    ("interaccion_personal_zh", r"(我在吃|我服用|医生给我开了).{0,20}(可以.{0,5}吃|吃.{0,5}安全吗|可以一起吃吗)"),
    ("pregunta_dosis_directa_personal_zh", rf"{_YO_ZH}.{{0,15}}应该吃多少|可以吃多少"),
    ("autodiagnostico_directo_zh", r"(这些症状|这个不舒服).{0,15}(可能是什么|是什么病)"),
]


def _buscar(patrones, texto_normalizado):
    return [nombre for nombre, patron in patrones if re.search(patron, texto_normalizado)]


def clasificar_consulta(texto: str) -> dict:
    """
    Devuelve {"categoria": "emergencia"|"riesgo_personal"|"educativo",
    "subtipo": "medica"|"salud_mental"|None, "señales": [nombres de
    patrones que matchearon]}.

    Prioridad: emergencia médica > emergencia de salud mental >
    riesgo personal > educativo. Nunca lanza excepción — texto vacío
    o None se clasifica como educativo sin señales.
    """
    if not texto or not texto.strip():
        return {"categoria": "educativo", "subtipo": None, "señales": []}

    normalizado = _normalizar(texto)

    señales = _buscar(PATRONES_EMERGENCIA_MEDICA, normalizado)
    if señales:
        return {"categoria": "emergencia", "subtipo": "medica", "señales": señales}

    señales = _buscar(PATRONES_EMERGENCIA_SALUD_MENTAL, normalizado)
    if señales:
        return {"categoria": "emergencia", "subtipo": "salud_mental", "señales": señales}

    señales = _buscar(PATRONES_RIESGO_PERSONAL, normalizado)
    if señales:
        return {"categoria": "riesgo_personal", "subtipo": None, "señales": señales}

    return {"categoria": "educativo", "subtipo": None, "señales": []}


# ---------------------------------------------------------------------
# Mensajes — centralizados aquí para que el texto exacto que ve el
# estudiante sea fácil de auditar/editar en un solo lugar.
#
# Multilingües a propósito y con especial cuidado en la traducción
# (más que cualquier otro texto de la app): son mensajes de seguridad
# que se muestran en el peor momento posible — si el estudiante tiene
# la UI en inglés o francés, un mensaje de emergencia en español que no
# entiende bien podría costarle segundos que importan. Los números de
# emergencia (911, Línea de la Vida) se mantienen igual en los 3
# idiomas porque son específicos de México — el texto alrededor se
# traduce, no el número.
# ---------------------------------------------------------------------

_MENSAJE_EMERGENCIA_MEDICA_POR_IDIOMA = {
    "es": (
        "🚨 Esto suena a una posible EMERGENCIA MÉDICA.\n\n"
        "Medicine Study AI es una herramienta educativa y NO puede evaluar ni tratar una emergencia real. "
        "Por favor:\n"
        "• Llama de inmediato al 911 (México) o al número de emergencias de tu país.\n"
        "• Si puedes, acude a la sala de urgencias más cercana ahora mismo.\n"
        "• No esperes una respuesta de esta app para actuar.\n\n"
        "Si en realidad esto es una consulta de estudio (por ejemplo, un caso clínico hipotético para un "
        "examen o una tarea), acláralo explícitamente en tu siguiente mensaje y con gusto te ayudo a analizarlo."
    ),
    "en": (
        "🚨 This sounds like a possible MEDICAL EMERGENCY.\n\n"
        "Medicine Study AI is an educational tool and CANNOT evaluate or treat a real emergency. Please:\n"
        "• Call 911 (Mexico) or your country's emergency number right now.\n"
        "• If you can, go to the nearest emergency room immediately.\n"
        "• Don't wait for a response from this app to act.\n\n"
        "If this is actually a study question (for example, a hypothetical clinical case for an exam or "
        "assignment), say so explicitly in your next message and I'll be glad to help you analyze it."
    ),
    "fr": (
        "🚨 Cela ressemble à une possible URGENCE MÉDICALE.\n\n"
        "Medicine Study AI est un outil éducatif et NE PEUT PAS évaluer ni traiter une urgence réelle. "
        "S'il te plaît :\n"
        "• Appelle immédiatement le 911 (Mexique) ou le numéro d'urgence de ton pays.\n"
        "• Si tu le peux, rends-toi aux urgences les plus proches tout de suite.\n"
        "• N'attends pas de réponse de cette application pour agir.\n\n"
        "S'il s'agit en réalité d'une question d'étude (par exemple, un cas clinique hypothétique pour un "
        "examen ou un devoir), précise-le explicitement dans ton prochain message et je serai heureux de "
        "t'aider à l'analyser."
    ),
    "de": (
        "🚨 Das klingt nach einem möglichen MEDIZINISCHEN NOTFALL.\n\n"
        "Medicine Study AI ist ein Lernwerkzeug und kann einen echten Notfall NICHT beurteilen oder "
        "behandeln. Bitte:\n"
        "• Rufe sofort die 911 (Mexiko) oder die Notrufnummer deines Landes an.\n"
        "• Geh, wenn möglich, sofort in die nächste Notaufnahme.\n"
        "• Warte nicht auf eine Antwort dieser App, um zu handeln.\n\n"
        "Falls es sich tatsächlich um eine Studienfrage handelt (z. B. einen hypothetischen klinischen Fall "
        "für eine Prüfung oder Hausaufgabe), sag das ausdrücklich in deiner nächsten Nachricht — dann helfe "
        "ich dir gerne bei der Analyse."
    ),
    "zh": (
        "🚨 这听起来像是可能的医疗紧急情况。\n\n"
        "Medicine Study AI 是一个教育工具，无法评估或处理真正的紧急情况。请：\n"
        "• 立即拨打 911（墨西哥）或你所在国家的急救电话。\n"
        "• 如果可以，请立即前往最近的急诊室。\n"
        "• 不要等待这个应用的回复才采取行动。\n\n"
        "如果这实际上是一个学习问题（例如，考试或作业中的一个假设临床病例），请在下一条消息中明确说明，"
        "我很乐意帮你分析。"
    ),
}

_MENSAJE_EMERGENCIA_SALUD_MENTAL_POR_IDIOMA = {
    "es": (
        "🚨 Si estás en peligro inmediato o pensando en hacerte daño, por favor busca ayuda ahora mismo:\n\n"
        "• México — Línea de la Vida: 800 911 2000 (24 horas, gratuita)\n"
        "• Emergencias: 911\n"
        "• Si estás fuera de México, contacta la línea de crisis local o los servicios de emergencia de tu país.\n\n"
        "No estás solo/a. Esta app es una herramienta de estudio y no puede reemplazar ayuda profesional — "
        "por favor habla con alguien de confianza o con un profesional de salud mental cuanto antes."
    ),
    "en": (
        "🚨 If you're in immediate danger or thinking about hurting yourself, please get help right now:\n\n"
        "• Mexico — Línea de la Vida: 800 911 2000 (24/7, free)\n"
        "• Emergencies: 911\n"
        "• If you're outside Mexico, contact your local crisis line or emergency services.\n\n"
        "You're not alone. This app is a study tool and cannot replace professional help — please talk to "
        "someone you trust or a mental health professional as soon as possible."
    ),
    "fr": (
        "🚨 Si tu es en danger immédiat ou que tu penses à te faire du mal, cherche de l'aide dès maintenant :\n\n"
        "• Mexique — Línea de la Vida : 800 911 2000 (24h/24, gratuit)\n"
        "• Urgences : 911\n"
        "• Si tu es hors du Mexique, contacte la ligne de crise locale ou les services d'urgence de ton pays.\n\n"
        "Tu n'es pas seul(e). Cette application est un outil d'étude et ne peut pas remplacer une aide "
        "professionnelle — parle à quelqu'un en qui tu as confiance ou à un professionnel de la santé "
        "mentale dès que possible."
    ),
    "de": (
        "🚨 Wenn du in unmittelbarer Gefahr bist oder daran denkst, dir selbst zu schaden, hol dir jetzt Hilfe:\n\n"
        "• Mexiko — Línea de la Vida: 800 911 2000 (rund um die Uhr, kostenlos)\n"
        "• Notruf: 911\n"
        "• Wenn du dich außerhalb Mexikos befindest, wende dich an die örtliche Krisenhotline oder den Notdienst deines Landes.\n\n"
        "Du bist nicht allein. Diese App ist ein Lernwerkzeug und kann professionelle Hilfe nicht ersetzen — "
        "bitte sprich so bald wie möglich mit jemandem, dem du vertraust, oder mit einer Fachperson für "
        "psychische Gesundheit."
    ),
    "zh": (
        "🚨 如果你正处于紧急危险中，或有伤害自己的想法，请立即寻求帮助：\n\n"
        "• 墨西哥 — Línea de la Vida 生命热线：800 911 2000（24小时，免费）\n"
        "• 紧急电话：911\n"
        "• 如果你不在墨西哥，请联系当地的危机热线或你所在国家的急救服务。\n\n"
        "你并不孤单。这个应用是一个学习工具，无法替代专业帮助——请尽快和你信任的人，"
        "或心理健康专业人士谈谈。"
    ),
}

_AVISO_RIESGO_PERSONAL_POR_IDIOMA = {
    "es": (
        "ℹ️ Esta pregunta suena como si fuera sobre tu propia salud o tratamiento, no un caso de estudio. "
        "Medicine Study AI es una herramienta EDUCATIVA — la respuesta de abajo es información general, no "
        "una indicación médica para ti. Para decisiones sobre tu salud, tu dosis o tu tratamiento, consulta "
        "a tu médico o farmacéutico."
    ),
    "en": (
        "ℹ️ This question sounds like it's about your own health or treatment, not a study case. Medicine "
        "Study AI is an EDUCATIONAL tool — the answer below is general information, not a medical "
        "recommendation for you. For decisions about your health, your dose, or your treatment, consult "
        "your doctor or pharmacist."
    ),
    "fr": (
        "ℹ️ Cette question semble porter sur ta propre santé ou ton propre traitement, pas sur un cas "
        "d'étude. Medicine Study AI est un outil ÉDUCATIF — la réponse ci-dessous est une information "
        "générale, pas une indication médicale pour toi. Pour toute décision concernant ta santé, ta dose "
        "ou ton traitement, consulte ton médecin ou ton pharmacien."
    ),
    "de": (
        "ℹ️ Diese Frage klingt so, als ginge es um deine eigene Gesundheit oder Behandlung, nicht um einen "
        "Studienfall. Medicine Study AI ist ein LERNWERKZEUG — die Antwort unten ist eine allgemeine "
        "Information, keine medizinische Empfehlung für dich. Für Entscheidungen über deine Gesundheit, "
        "deine Dosis oder deine Behandlung wende dich an deinen Arzt oder Apotheker."
    ),
    "zh": (
        "ℹ️ 这个问题听起来是关于你自己的健康或治疗，而不是一个学习案例。Medicine Study AI 是一个"
        "教育工具——下面的回答是一般性信息，不是针对你的医疗建议。关于你的健康、剂量或治疗的决定，"
        "请咨询你的医生或药剂师。"
    ),
}

_INSTRUCCION_REFUERZO_RIESGO_PERSONAL_POR_IDIOMA = {
    "es": (
        "\n\n[Nota interna — no visible para el estudiante como tal: esta consulta parece referirse a la "
        "situación de salud PERSONAL del usuario, no a un caso de estudio académico. Responde de forma "
        "educativa y general, NO receta una dosis específica ni un cambio de tratamiento para esta persona, "
        "y recuérdale explícitamente que consulte a su médico o farmacéutico para su caso concreto.]"
    ),
    "en": (
        "\n\n[Internal note — not shown to the student as such: this query seems to refer to the user's "
        "PERSONAL health situation, not an academic study case. Answer in an educational, general way, do "
        "NOT prescribe a specific dose or treatment change for this person, and explicitly remind them to "
        "consult their doctor or pharmacist for their specific case.]"
    ),
    "fr": (
        "\n\n[Note interne — non visible en tant que telle pour l'étudiant : cette question semble porter "
        "sur la situation de santé PERSONNELLE de l'utilisateur, pas sur un cas d'étude académique. Réponds "
        "de façon éducative et générale, NE prescris PAS de dose spécifique ni de changement de traitement "
        "pour cette personne, et rappelle-lui explicitement de consulter son médecin ou son pharmacien pour "
        "son cas précis.]"
    ),
    "de": (
        "\n\n[Interner Hinweis — für den Studierenden als solcher nicht sichtbar: Diese Anfrage scheint sich "
        "auf die PERSÖNLICHE Gesundheitssituation der Person zu beziehen, nicht auf einen akademischen "
        "Studienfall. Antworte auf eine lehrreiche, allgemeine Weise, verschreibe KEINE konkrete Dosis oder "
        "Behandlungsänderung für diese Person, und erinnere sie ausdrücklich daran, für ihren konkreten "
        "Fall ihren Arzt oder Apotheker zu konsultieren.]"
    ),
    "zh": (
        "\n\n[内部提示——学生看不到这条提示本身：这个问题似乎涉及用户自己的个人健康状况，"
        "而不是一个学术学习案例。请以教育性、通用的方式回答，不要为这个人开具具体的剂量或"
        "治疗方案变更建议，并明确提醒对方就其具体情况咨询医生或药剂师。]"
    ),
}


def _msg(diccionario, idioma):
    return diccionario.get(idioma, diccionario["es"])


def mensaje_emergencia_medica(idioma: str = "es") -> str:
    return _msg(_MENSAJE_EMERGENCIA_MEDICA_POR_IDIOMA, idioma)


def mensaje_emergencia_salud_mental(idioma: str = "es") -> str:
    return _msg(_MENSAJE_EMERGENCIA_SALUD_MENTAL_POR_IDIOMA, idioma)


def aviso_riesgo_personal(idioma: str = "es") -> str:
    return _msg(_AVISO_RIESGO_PERSONAL_POR_IDIOMA, idioma)


def instruccion_refuerzo_riesgo_personal(idioma: str = "es") -> str:
    return _msg(_INSTRUCCION_REFUERZO_RIESGO_PERSONAL_POR_IDIOMA, idioma)


# Compatibilidad hacia atrás: código existente que importe estas
# constantes directamente sigue funcionando (equivalen al idioma por
# defecto, español) — pero app_ui.py ahora usa las funciones de arriba
# con el idioma seleccionado por el estudiante.
MENSAJE_EMERGENCIA_MEDICA = mensaje_emergencia_medica("es")
MENSAJE_EMERGENCIA_SALUD_MENTAL = mensaje_emergencia_salud_mental("es")
AVISO_RIESGO_PERSONAL = aviso_riesgo_personal("es")
INSTRUCCION_REFUERZO_RIESGO_PERSONAL = instruccion_refuerzo_riesgo_personal("es")
