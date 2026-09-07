"""
Traducciones de la interfaz (Fase 9 — multilingüe de verdad).

Antes, cambiar el idioma solo afectaba las respuestas de la IA — el
resto de la interfaz (calculadoras, examen, flashcards, sidebar) se
quedaba en español, lo cual no tenía sentido: de qué sirve responder en
inglés si el estudiante no entiende para qué es cada campo de la
calculadora de función renal.

Diseño: un diccionario plano TEXTOS[clave][idioma] = texto, y una sola
función de acceso t(clave, idioma). Si falta una clave o un idioma, cae
a español y NUNCA lanza excepción ni deja una etiqueta vacía — en el
peor de los casos se ve la clave cruda entre corchetes, lo cual es una
señal visible de "falta traducir esto" en vez de un texto vacío
silencioso que nadie nota.

Idiomas soportados: es, en, fr, de, zh (alemán y chino simplificado
agregados en la Fase 10, mismo diseño). El texto de dosificación y de
interacciones (AJUSTES_RENALES_COMUNES, BASE_INTERACCIONES) sigue
excluido a propósito — ver calculadoras_clinicas.py e
interacciones_farmacologicas.py.
"""

TEXTOS = {
    # ---------------------------------------------------------------
    # Sidebar / navegación general
    # ---------------------------------------------------------------
    "sidebar_titulo": {"es": "Medicine AI", "en": "Medicine AI", "fr": "Medicine AI", "de": "Medicine AI", "zh": "Medicine AI"},
    "cerrar_sesion": {"es": "Cerrar sesión", "en": "Log out", "fr": "Se déconnecter", "de": "Abmelden", "zh": "退出登录"},
    "nuevo_chat": {"es": "+ Nuevo Chat", "en": "+ New Chat", "fr": "+ Nouvelle conversation", "de": "+ Neuer Chat", "zh": "+ 新对话"},
    "cargar_pdf": {"es": "Cargar PDF", "en": "Upload PDF", "fr": "Charger un PDF", "de": "PDF hochladen", "zh": "上传 PDF"},
    "idioma_respuesta": {"es": "🌐 Idioma de respuesta", "en": "🌐 Response language", "fr": "🌐 Langue de réponse", "de": "🌐 Antwortsprache", "zh": "🌐 回答语言"},
    "busqueda_pubmed": {"es": "Búsqueda PubMed", "en": "PubMed search", "fr": "Recherche PubMed", "de": "PubMed-Suche", "zh": "PubMed 搜索"},
    "nivel_evidencia": {"es": "Nivel de evidencia", "en": "Evidence level", "fr": "Niveau de preuve", "de": "Evidenzgrad", "zh": "证据级别"},
    "verificar_factualidad": {"es": "Verificar factualidad", "en": "Verify factuality", "fr": "Vérifier la factualité", "de": "Faktentreue prüfen", "zh": "核实真实性"},
    "seccion_flashcards": {"es": "Flashcards", "en": "Flashcards", "fr": "Cartes mémo", "de": "Karteikarten", "zh": "记忆卡"},
    "generar_de_un_tema": {"es": "Generar de un tema", "en": "Generate from a topic", "fr": "Générer à partir d'un sujet", "de": "Aus einem Thema erstellen", "zh": "根据主题生成"},
    "tooltip_escribe_tema": {
        "es": "Escribe un tema en el cuadro de mensaje y presiona aquí",
        "en": "Type a topic in the message box and press here",
        "fr": "Écris un sujet dans la zone de message et clique ici",
        "de": "Schreibe ein Thema in das Nachrichtenfeld und klicke hier",
        "zh": "在消息框中输入主题，然后点击这里",
    },
    "repasar": {"es": "📇 Repasar ({n} pendientes)", "en": "📇 Review ({n} pending)", "fr": "📇 Réviser ({n} en attente)", "de": "📇 Wiederholen ({n} ausstehend)", "zh": "📇 复习（待复习 {n} 张）"},
    "seccion_examen": {"es": "Examen", "en": "Exam", "fr": "Examen", "de": "Prüfung", "zh": "考试"},
    "generar_examen_de_un_tema": {
        "es": "Generar examen de un tema", "en": "Generate exam from a topic", "fr": "Générer un examen sur un sujet",
        "de": "Prüfung zu einem Thema erstellen", "zh": "根据主题生成考试",
    },
    "mi_progreso": {"es": "📊 Mi progreso", "en": "📊 My progress", "fr": "📊 Ma progression", "de": "📊 Mein Fortschritt", "zh": "📊 我的进度"},
    "calculadoras_clinicas": {"es": "🧮 Calculadoras clínicas", "en": "🧮 Clinical calculators", "fr": "🧮 Calculatrices cliniques", "de": "🧮 Klinische Rechner", "zh": "🧮 临床计算器"},
    "historial_consultas": {"es": "Historial de Consultas", "en": "Chat history", "fr": "Historique des consultations", "de": "Gesprächsverlauf", "zh": "咨询记录"},
    "entrada_hint": {
        "es": "Pregunta algo sobre medicina o tu PDF...",
        "en": "Ask something about medicine or your PDF...",
        "fr": "Pose une question sur la médecine ou ton PDF...",
        "de": "Stelle eine Frage zur Medizin oder zu deinem PDF...",
        "zh": "问一个关于医学或你的 PDF 的问题…",
    },
    "volver_al_chat": {"es": "← Volver al chat", "en": "← Back to chat", "fr": "← Retour au chat", "de": "← Zurück zum Chat", "zh": "← 返回聊天"},
    "confirmar_eliminar_titulo": {
        "es": "¿Eliminar conversación?", "en": "Delete conversation?", "fr": "Supprimer la conversation ?",
        "de": "Unterhaltung löschen?", "zh": "删除对话？",
    },
    "confirmar_eliminar_texto": {
        "es": "Esta acción no se puede deshacer.", "en": "This action cannot be undone.", "fr": "Cette action est irréversible.",
        "de": "Diese Aktion kann nicht rückgängig gemacht werden.", "zh": "此操作无法撤销。",
    },
    "cancelar": {"es": "Cancelar", "en": "Cancel", "fr": "Annuler", "de": "Abbrechen", "zh": "取消"},
    "eliminar": {"es": "Eliminar", "en": "Delete", "fr": "Supprimer", "de": "Löschen", "zh": "删除"},

    # ---------------------------------------------------------------
    # Modos de evidencia (dropdown "Nivel de evidencia")
    # ---------------------------------------------------------------
    "modo_evidencia_todo": {"es": "Todo", "en": "All", "fr": "Tout", "de": "Alles", "zh": "全部"},
    "modo_evidencia_primaria": {"es": "Solo evidencia primaria", "en": "Primary evidence only", "fr": "Preuves primaires seulement", "de": "Nur Primärevidenz", "zh": "仅一手证据"},
    "modo_evidencia_revision_guia": {"es": "Revisiones y guías", "en": "Reviews and guidelines", "fr": "Revues et recommandations", "de": "Übersichtsarbeiten und Leitlinien", "zh": "综述与指南"},
    "modo_evidencia_sin_opiniones": {"es": "Ocultar opiniones", "en": "Hide opinions", "fr": "Masquer les opinions", "de": "Meinungen ausblenden", "zh": "隐藏观点类文献"},

    # ---------------------------------------------------------------
    # Pantalla de bienvenida
    # ---------------------------------------------------------------
    "bienvenida_subtitulo": {
        "es": "Tu asistente de estudio para medicina — con evidencia citable y verificación de factualidad",
        "en": "Your medical study assistant — with citable evidence and factuality verification",
        "fr": "Ton assistant d'étude en médecine — avec preuves citables et vérification de factualité",
        "de": "Dein Studienassistent für Medizin — mit zitierfähiger Evidenz und Faktenprüfung",
        "zh": "你的医学学习助手——提供可引用的证据并核实事实准确性",
    },
    "func_pubmed_titulo": {"es": "Búsqueda en PubMed", "en": "PubMed search", "fr": "Recherche PubMed", "de": "PubMed-Suche", "zh": "PubMed 搜索"},
    "func_pubmed_desc": {
        "es": "Papers reales, ordenados por relevancia semántica",
        "en": "Real papers, ranked by semantic relevance",
        "fr": "De vrais articles, classés par pertinence sémantique",
        "de": "Echte Studien, sortiert nach semantischer Relevanz",
        "zh": "真实文献，按语义相关性排序",
    },
    "func_pdfs_titulo": {"es": "Tus PDFs", "en": "Your PDFs", "fr": "Tes PDF", "de": "Deine PDFs", "zh": "你的 PDF"},
    "func_pdfs_desc": {
        "es": "Sube apuntes o papers y pregúntale directo al documento",
        "en": "Upload notes or papers and ask the document directly",
        "fr": "Charge des notes ou des articles et interroge le document directement",
        "de": "Lade Notizen oder Studien hoch und frag direkt das Dokument",
        "zh": "上传笔记或文献，直接向文档提问",
    },
    "func_factualidad_titulo": {"es": "Factualidad verificada", "en": "Verified factuality", "fr": "Factualité vérifiée", "de": "Geprüfte Faktentreue", "zh": "已核实的真实性"},
    "func_factualidad_desc": {
        "es": "Cada afirmación se contrasta contra las fuentes citadas",
        "en": "Every claim is checked against the cited sources",
        "fr": "Chaque affirmation est vérifiée par rapport aux sources citées",
        "de": "Jede Aussage wird mit den zitierten Quellen abgeglichen",
        "zh": "每条陈述都会与引用的来源进行核对",
    },
    "func_calculadoras_titulo": {"es": "Calculadoras clínicas", "en": "Clinical calculators", "fr": "Calculatrices cliniques", "de": "Klinische Rechner", "zh": "临床计算器"},
    "func_calculadoras_desc": {
        "es": "IMC, función renal, dosis, interacciones",
        "en": "BMI, renal function, dosing, interactions",
        "fr": "IMC, fonction rénale, doses, interactions",
        "de": "BMI, Nierenfunktion, Dosierung, Wechselwirkungen",
        "zh": "BMI、肾功能、剂量、药物相互作用",
    },
    "prueba_con_algo_como": {"es": "Prueba con algo como:", "en": "Try something like:", "fr": "Essaie quelque chose comme :", "de": "Probier zum Beispiel:", "zh": "试试这样的问题："},
    "chip_ciclo_cardiaco": {
        "es": "Explícame el ciclo cardíaco", "en": "Explain the cardiac cycle", "fr": "Explique-moi le cycle cardiaque",
        "de": "Erkläre mir den Herzzyklus", "zh": "给我讲讲心动周期",
    },
    "chip_dolor_toracico": {
        "es": "Diagnóstico diferencial de dolor torácico",
        "en": "Differential diagnosis of chest pain",
        "fr": "Diagnostic différentiel de la douleur thoracique",
        "de": "Differentialdiagnose von Brustschmerzen",
        "zh": "胸痛的鉴别诊断",
    },
    "chip_metformina": {
        "es": "Mecanismo de acción de la metformina",
        "en": "Mechanism of action of metformin",
        "fr": "Mécanisme d'action de la metformine",
        "de": "Wirkmechanismus von Metformin",
        "zh": "二甲双胍的作用机制",
    },

    # ---------------------------------------------------------------
    # Proceso / indicadores de carga (panel colapsable "Ver proceso")
    # ---------------------------------------------------------------
    "ver_proceso": {"es": "Ver proceso", "en": "View process", "fr": "Voir le processus", "de": "Prozess anzeigen", "zh": "查看处理过程"},
    "buscando_pubmed": {"es": "Buscando en PubMed...", "en": "Searching PubMed...", "fr": "Recherche dans PubMed...", "de": "Suche in PubMed...", "zh": "正在搜索 PubMed…"},
    "generando_respuesta": {"es": "Generando respuesta...", "en": "Generating response...", "fr": "Génération de la réponse...", "de": "Antwort wird erstellt...", "zh": "正在生成回答…"},
    "respuesta_generada": {"es": "Respuesta generada", "en": "Response generated", "fr": "Réponse générée", "de": "Antwort erstellt", "zh": "回答已生成"},
    "verificando_afirmaciones": {"es": "Verificando afirmaciones...", "en": "Verifying claims...", "fr": "Vérification des affirmations...", "de": "Aussagen werden geprüft...", "zh": "正在核实陈述…"},
    "afirmaciones_verificadas": {"es": "Afirmaciones verificadas", "en": "Claims verified", "fr": "Affirmations vérifiées", "de": "Aussagen geprüft", "zh": "陈述已核实"},

    # ---------------------------------------------------------------
    # Niveles de jerarquía de evidencia (pubmed_search.py) — se muestran
    # vía t_categoria() en el badge de evidencia citada.
    # ---------------------------------------------------------------
    "niv_meta_analisis": {"es": "Revisión (meta-análisis)", "en": "Review (meta-analysis)", "fr": "Revue (méta-analyse)", "de": "Übersichtsarbeit (Metaanalyse)", "zh": "综述（荟萃分析）"},
    "niv_revision_sistematica": {"es": "Revisión (sistemática)", "en": "Review (systematic)", "fr": "Revue (systématique)", "de": "Übersichtsarbeit (systematisch)", "zh": "综述（系统性）"},
    "niv_guia_clinica": {"es": "Guía clínica", "en": "Clinical guideline", "fr": "Recommandation clinique", "de": "Klinische Leitlinie", "zh": "临床指南"},
    "niv_ensayo_aleatorizado": {"es": "Evidencia primaria (ensayo clínico aleatorizado)", "en": "Primary evidence (randomized controlled trial)", "fr": "Preuve primaire (essai randomisé contrôlé)", "de": "Primärevidenz (randomisierte kontrollierte Studie)", "zh": "一手证据（随机对照试验）"},
    "niv_ensayo_clinico": {"es": "Evidencia primaria (ensayo clínico)", "en": "Primary evidence (clinical trial)", "fr": "Preuve primaire (essai clinique)", "de": "Primärevidenz (klinische Studie)", "zh": "一手证据（临床试验）"},
    "niv_observacional": {"es": "Evidencia primaria (observacional)", "en": "Primary evidence (observational)", "fr": "Preuve primaire (observationnelle)", "de": "Primärevidenz (Beobachtungsstudie)", "zh": "一手证据（观察性研究）"},
    "niv_reporte_caso": {"es": "Evidencia primaria (reporte de caso)", "en": "Primary evidence (case report)", "fr": "Preuve primaire (étude de cas)", "de": "Primärevidenz (Fallbericht)", "zh": "一手证据（病例报告）"},
    "niv_revision_narrativa": {"es": "Revisión (narrativa)", "en": "Review (narrative)", "fr": "Revue (narrative)", "de": "Übersichtsarbeit (narrativ)", "zh": "综述（叙述性）"},
    "niv_opinion": {"es": "Opinión/comentario", "en": "Opinion/commentary", "fr": "Opinion/commentaire", "de": "Meinung/Kommentar", "zh": "观点/评论"},
    "niv_preprint": {"es": "Preprint (sin revisión por pares)", "en": "Preprint (not peer-reviewed)", "fr": "Préimpression (non révisée par les pairs)", "de": "Preprint (nicht begutachtet)", "zh": "预印本（未经同行评审）"},
    "niv_sin_clasificar": {"es": "Sin clasificar", "en": "Unclassified", "fr": "Non classé", "de": "Nicht klassifiziert", "zh": "未分类"},

    "badge_evidencia_citada": {
        "es": "Evidencia más fuerte citada: {nivel} ({n} fuente(s))",
        "en": "Strongest evidence cited: {nivel} ({n} source(s))",
        "fr": "Preuve la plus solide citée : {nivel} ({n} source(s))",
        "de": "Stärkste zitierte Evidenz: {nivel} ({n} Quelle(n))",
        "zh": "所引用的最强证据：{nivel}（共 {n} 个来源）",
    },
    "copiar_respuesta": {"es": "Copiar respuesta", "en": "Copy answer", "fr": "Copier la réponse", "de": "Antwort kopieren", "zh": "复制回答"},
    "copiado_portapapeles": {"es": "📋 Copiado al portapapeles", "en": "📋 Copied to clipboard", "fr": "📋 Copié dans le presse-papiers", "de": "📋 In die Zwischenablage kopiert", "zh": "📋 已复制到剪贴板"},
    "feedback_util": {"es": "Esta respuesta me sirvió", "en": "This answer was helpful", "fr": "Cette réponse m'a aidé", "de": "Diese Antwort war hilfreich", "zh": "这个回答有帮助"},
    "feedback_no_util": {"es": "Esta respuesta no me sirvió", "en": "This answer wasn't helpful", "fr": "Cette réponse ne m'a pas aidé", "de": "Diese Antwort war nicht hilfreich", "zh": "这个回答没有帮助"},
    "feedback_gracias": {"es": "Gracias por tu feedback 🙏", "en": "Thanks for your feedback 🙏", "fr": "Merci pour ton retour 🙏", "de": "Danke für dein Feedback 🙏", "zh": "感谢你的反馈🙏"},
    "verificando_terminologia_icd11": {
        "es": "Verificando terminología ICD-11...", "en": "Checking ICD-11 terminology...",
        "fr": "Vérification de la terminologie ICD-11...", "de": "ICD-11-Terminologie wird geprüft...",
        "zh": "正在核实 ICD-11 术语…",
    },
    "terminologia_icd11_verificada": {
        "es": "{n} término(s) verificados con ICD-11", "en": "{n} term(s) verified with ICD-11",
        "fr": "{n} terme(s) vérifié(s) avec ICD-11", "de": "{n} Begriff(e) mit ICD-11 geprüft",
        "zh": "已通过 ICD-11 核实 {n} 个术语",
    },
    "icd11_sin_terminos": {
        "es": "ICD-11: sin términos médicos específicos que verificar",
        "en": "ICD-11: no specific medical terms to verify",
        "fr": "ICD-11 : aucun terme médical spécifique à vérifier",
        "de": "ICD-11: keine spezifischen medizinischen Begriffe zu prüfen",
        "zh": "ICD-11：没有需要核实的具体医学术语",
    },
    "pubmed_sin_resultados": {
        "es": "PubMed: sin papers relevantes ({n} únicos ya guardados)",
        "en": "PubMed: no relevant papers ({n} unique already saved)",
        "fr": "PubMed : aucun article pertinent ({n} uniques déjà enregistrés)",
        "de": "PubMed: keine relevanten Studien ({n} bereits gespeichert)",
        "zh": "PubMed：未找到相关文献（已保存 {n} 篇独立文献）",
    },
    "pubmed_con_resultados": {
        "es": "PubMed: {n} paper(s) relevantes encontrados",
        "en": "PubMed: {n} relevant paper(s) found",
        "fr": "PubMed : {n} article(s) pertinent(s) trouvé(s)",
        "de": "PubMed: {n} relevante Studie(n) gefunden",
        "zh": "PubMed：找到 {n} 篇相关文献",
    },
    "fragmentos_usados": {
        "es": "{n} fragmento(s) de tus documentos usados como contexto",
        "en": "{n} fragment(s) from your documents used as context",
        "fr": "{n} fragment(s) de tes documents utilisés comme contexte",
        "de": "{n} Abschnitt(e) aus deinen Dokumenten als Kontext verwendet",
        "zh": "使用了你文档中的 {n} 个片段作为上下文",
    },
    "error_pubmed": {"es": "Error buscando en PubMed: {error}", "en": "Error searching PubMed: {error}", "fr": "Erreur de recherche PubMed : {error}", "de": "Fehler bei der PubMed-Suche: {error}", "zh": "搜索 PubMed 时出错：{error}"},
    "api_no_configurado": {
        "es": "❌ API Client no configurado.", "en": "❌ API client not configured.", "fr": "❌ Client API non configuré.",
        "de": "❌ API-Client nicht konfiguriert.", "zh": "❌ API 客户端未配置。",
    },
    "transfiriendo_archivo": {
        "es": "⏳ Transfiriendo archivo...", "en": "⏳ Uploading file...", "fr": "⏳ Transfert du fichier...",
        "de": "⏳ Datei wird übertragen...", "zh": "⏳ 正在传输文件…",
    },
    "procesando_pdf": {
        "es": "⏳ Procesando y extrayendo texto del PDF...",
        "en": "⏳ Processing and extracting text from the PDF...",
        "fr": "⏳ Traitement et extraction du texte du PDF...",
        "de": "⏳ PDF wird verarbeitet und Text extrahiert...",
        "zh": "⏳ 正在处理并提取 PDF 文本…",
    },
    "archivo_no_identificado": {
        "es": "❌ Archivo no identificado", "en": "❌ File not recognized", "fr": "❌ Fichier non identifié",
        "de": "❌ Datei nicht erkannt", "zh": "❌ 无法识别文件",
    },
    "error_subir_archivo": {
        "es": "❌ Error al subir el archivo: {error}", "en": "❌ Error uploading the file: {error}", "fr": "❌ Erreur lors du téléchargement du fichier : {error}",
        "de": "❌ Fehler beim Hochladen der Datei: {error}", "zh": "❌ 上传文件时出错：{error}",
    },
    "pdf_indexado_con_ocr": {
        "es": "✅ PDF indexado ({n} fragmentos, {n_ocr} págs. vía OCR): {nombre}...",
        "en": "✅ PDF indexed ({n} fragments, {n_ocr} pages via OCR): {nombre}...",
        "fr": "✅ PDF indexé ({n} fragments, {n_ocr} pages via OCR) : {nombre}...",
        "de": "✅ PDF indiziert ({n} Abschnitte, {n_ocr} Seiten per OCR): {nombre}...",
        "zh": "✅ PDF 已索引（{n} 个片段，{n_ocr} 页通过 OCR）：{nombre}…",
    },
    "pdf_indexado": {
        "es": "✅ PDF indexado ({n} fragmentos): {nombre}...",
        "en": "✅ PDF indexed ({n} fragments): {nombre}...",
        "fr": "✅ PDF indexé ({n} fragments) : {nombre}...",
        "de": "✅ PDF indiziert ({n} Abschnitte): {nombre}...",
        "zh": "✅ PDF 已索引（{n} 个片段）：{nombre}…",
    },
    "pdf_cargado_sin_busqueda": {
        "es": "✅ PDF cargado (sin búsqueda semántica): {nombre}...",
        "en": "✅ PDF uploaded (no semantic search): {nombre}...",
        "fr": "✅ PDF chargé (sans recherche sémantique) : {nombre}...",
        "de": "✅ PDF hochgeladen (ohne semantische Suche): {nombre}...",
        "zh": "✅ PDF 已上传（无语义搜索）：{nombre}…",
    },
    "pdf_sin_ocr_disponible": {
        "es": "❌ No se pudo extraer texto (parece escaneado; el OCR no está disponible en este servidor)",
        "en": "❌ Could not extract text (looks scanned; OCR is not available on this server)",
        "fr": "❌ Impossible d'extraire le texte (semble scanné ; l'OCR n'est pas disponible sur ce serveur)",
        "de": "❌ Text konnte nicht extrahiert werden (scheint gescannt zu sein; OCR ist auf diesem Server nicht verfügbar)",
        "zh": "❌ 无法提取文本（似乎是扫描件；此服务器不支持 OCR）",
    },
    "pdf_sin_texto_ni_ocr": {
        "es": "❌ No se pudo extraer texto del PDF, ni siquiera con OCR",
        "en": "❌ Could not extract text from the PDF, not even with OCR",
        "fr": "❌ Impossible d'extraire le texte du PDF, même avec l'OCR",
        "de": "❌ Aus dem PDF konnte kein Text extrahiert werden, auch nicht mit OCR",
        "zh": "❌ 即使使用 OCR 也无法从 PDF 中提取文本",
    },
    "no_se_pudo_procesar_pdf": {
        "es": "❌ No se pudo procesar el PDF: {error}", "en": "❌ Could not process the PDF: {error}", "fr": "❌ Impossible de traiter le PDF : {error}",
        "de": "❌ PDF konnte nicht verarbeitet werden: {error}", "zh": "❌ 无法处理 PDF：{error}",
    },
    "error_generico": {"es": "❌ Error: {error}", "en": "❌ Error: {error}", "fr": "❌ Erreur : {error}", "de": "❌ Fehler: {error}", "zh": "❌ 错误：{error}"},

    # ---------------------------------------------------------------
    # Mensajes de validación de calculadoras_clinicas.py — antes fijos
    # en español sin importar el idioma de la UI.
    # ---------------------------------------------------------------
    "err_peso_altura_numeros": {
        "es": "Peso y altura deben ser números.", "en": "Weight and height must be numbers.", "fr": "Le poids et la taille doivent être des nombres.",
        "de": "Gewicht und Größe müssen Zahlen sein.", "zh": "体重和身高必须为数字。",
    },
    "err_peso_altura_mayores_cero": {
        "es": "Peso y altura deben ser mayores que cero.", "en": "Weight and height must be greater than zero.", "fr": "Le poids et la taille doivent être supérieurs à zéro.",
        "de": "Gewicht und Größe müssen größer als null sein.", "zh": "体重和身高必须大于零。",
    },
    "err_edad_peso_creatinina_numeros": {
        "es": "Edad, peso y creatinina deben ser números.", "en": "Age, weight, and creatinine must be numbers.", "fr": "L'âge, le poids et la créatinine doivent être des nombres.",
        "de": "Alter, Gewicht und Kreatinin müssen Zahlen sein.", "zh": "年龄、体重和肌酐必须为数字。",
    },
    "err_edad_peso_creatinina_mayores_cero": {
        "es": "Edad, peso y creatinina deben ser mayores que cero.",
        "en": "Age, weight, and creatinine must be greater than zero.",
        "fr": "L'âge, le poids et la créatinine doivent être supérieurs à zéro.",
        "de": "Alter, Gewicht und Kreatinin müssen größer als null sein.",
        "zh": "年龄、体重和肌酐必须大于零。",
    },
    "err_sexo_m_f": {"es": "Sexo debe ser 'M' o 'F'.", "en": "Sex must be 'M' or 'F'.", "fr": "Le sexe doit être « M » ou « F ».", "de": "Geschlecht muss 'M' oder 'F' sein.", "zh": "性别必须为“M”或“F”。"},
    "err_edad_creatinina_numeros": {
        "es": "Edad y creatinina deben ser números.", "en": "Age and creatinine must be numbers.", "fr": "L'âge et la créatinine doivent être des nombres.",
        "de": "Alter und Kreatinin müssen Zahlen sein.", "zh": "年龄和肌酐必须为数字。",
    },
    "err_edad_creatinina_mayores_cero": {
        "es": "Edad y creatinina deben ser mayores que cero.", "en": "Age and creatinine must be greater than zero.", "fr": "L'âge et la créatinine doivent être supérieurs à zéro.",
        "de": "Alter und Kreatinin müssen größer als null sein.", "zh": "年龄和肌酐必须大于零。",
    },
    "err_peso_dosiskg_numeros": {
        "es": "Peso y dosis por kg deben ser números.", "en": "Weight and dose per kg must be numbers.", "fr": "Le poids et la dose par kg doivent être des nombres.",
        "de": "Gewicht und Dosis pro kg müssen Zahlen sein.", "zh": "体重和每公斤剂量必须为数字。",
    },
    "err_peso_dosiskg_mayores_cero": {
        "es": "Peso y dosis por kg deben ser mayores que cero.",
        "en": "Weight and dose per kg must be greater than zero.",
        "fr": "Le poids et la dose par kg doivent être supérieurs à zéro.",
        "de": "Gewicht und Dosis pro kg müssen größer als null sein.",
        "zh": "体重和每公斤剂量必须大于零。",
    },
    "err_aclaramiento_numero": {
        "es": "El aclaramiento debe ser un número.", "en": "Clearance must be a number.", "fr": "La clairance doit être un nombre.",
        "de": "Die Clearance muss eine Zahl sein.", "zh": "清除率必须为数字。",
    },
    "err_falta_aclaramiento": {
        "es": "Falta el aclaramiento de creatinina.", "en": "Creatinine clearance is missing.", "fr": "La clairance de la créatinine est manquante.",
        "de": "Die Kreatinin-Clearance fehlt.", "zh": "缺少肌酐清除率。",
    },
    "err_escribe_farmaco": {
        "es": "Escribe el nombre del fármaco.", "en": "Enter the drug name.", "fr": "Indique le nom du médicament.",
        "de": "Gib den Namen des Medikaments ein.", "zh": "请输入药物名称。",
    },
    "nota_peso_ajustado": {
        "es": "usando peso ajustado: {valor} kg", "en": "using adjusted weight: {valor} kg", "fr": "poids ajusté utilisé : {valor} kg",
        "de": "verwendetes angepasstes Gewicht: {valor} kg", "zh": "使用校正体重：{valor} kg",
    },
    "ajuste_no_encontrado": {
        "es": "'{farmaco}' no está en la tabla de referencia local. Consulta la ficha técnica actualizada antes de ajustar la dosis.",
        "en": "'{farmaco}' is not in the local reference table. Check the current prescribing information or an updated clinical source before adjusting the dose.",
        "fr": "« {farmaco} » n'est pas dans le tableau de référence local. Consulte la notice officielle en vigueur ou une source clinique à jour avant d'ajuster la dose.",
        "de": "'{farmaco}' ist nicht in der lokalen Referenztabelle enthalten. Prüfe die aktuelle Fachinformation oder eine aktuelle klinische Quelle, bevor du die Dosis anpasst.",
        "zh": "本地参考表中没有“{farmaco}”。在调整剂量之前，请查阅现行说明书或最新的临床资料。",
    },
    "ajuste_sin_banda": {
        "es": "No se encontró una banda aplicable para ese aclaramiento.",
        "en": "No applicable band was found for that clearance value.",
        "fr": "Aucune tranche applicable n'a été trouvée pour cette clairance.",
        "de": "Für diesen Clearance-Wert wurde kein passender Bereich gefunden.",
        "zh": "未找到适用于该清除率的剂量区间。",
    },

    # ---------------------------------------------------------------
    # limite_uso.py — mensaje de límite de solicitudes alcanzado
    # ---------------------------------------------------------------
    "limite_alcanzado": {
        "es": "Alcanzaste el límite de {maximo} solicitudes de '{tipo}' por {etiqueta}. Espera un momento antes de volver a intentarlo — este límite protege la cuota compartida de la IA para todos los usuarios.",
        "en": "You've reached the limit of {maximo} '{tipo}' requests per {etiqueta}. Wait a moment before trying again — this limit protects the shared AI quota for all users.",
        "fr": "Tu as atteint la limite de {maximo} requêtes « {tipo} » par {etiqueta}. Attends un instant avant de réessayer — cette limite protège le quota d'IA partagé pour tous les utilisateurs.",
        "de": "Du hast das Limit von {maximo} '{tipo}'-Anfragen pro {etiqueta} erreicht. Warte einen Moment, bevor du es erneut versuchst — dieses Limit schützt das gemeinsame KI-Kontingent für alle Nutzer.",
        "zh": "你已达到每{etiqueta} {maximo} 次“{tipo}”请求的上限。请稍等片刻再试——此限制用于保护所有用户共享的 AI 配额。",
    },
    "ventana_minuto": {"es": "minuto", "en": "minute", "fr": "minute", "de": "Minute", "zh": "分钟"},
    "ventana_hora": {"es": "hora", "en": "hour", "fr": "heure", "de": "Stunde", "zh": "小时"},
    "ventana_dia": {"es": "día", "en": "day", "fr": "jour", "de": "Tag", "zh": "天"},

    # ---------------------------------------------------------------
    # interacciones_farmacologicas.py — respaldo de IA
    # ---------------------------------------------------------------
    "groq_no_configurado": {
        "es": "El cliente de Groq no está configurado (falta GROQ_API_KEY).",
        "en": "The Groq client is not configured (GROQ_API_KEY is missing).",
        "fr": "Le client Groq n'est pas configuré (GROQ_API_KEY manquante).",
        "de": "Der Groq-Client ist nicht konfiguriert (GROQ_API_KEY fehlt).",
        "zh": "Groq 客户端未配置（缺少 GROQ_API_KEY）。",
    },
    "modelo_sin_texto": {
        "es": "El modelo no devolvió texto.", "en": "The model did not return any text.", "fr": "Le modèle n'a renvoyé aucun texte.",
        "de": "Das Modell hat keinen Text zurückgegeben.", "zh": "模型未返回任何文本。",
    },
    "error_llamando_groq": {
        "es": "Error llamando a Groq: {error}", "en": "Error calling Groq: {error}", "fr": "Erreur lors de l'appel à Groq : {error}",
        "de": "Fehler beim Aufruf von Groq: {error}", "zh": "调用 Groq 时出错：{error}",
    },
    "error_cargando_pantalla_principal": {
        "es": "❌ Error cargando la pantalla principal: {error}",
        "en": "❌ Error loading the main screen: {error}",
        "fr": "❌ Erreur lors du chargement de l'écran principal : {error}",
        "de": "❌ Fehler beim Laden des Hauptbildschirms: {error}",
        "zh": "❌ 加载主界面时出错：{error}",
    },
    "consulta_medica_default": {"es": "Consulta Médica", "en": "Medical Query", "fr": "Consultation Médicale", "de": "Medizinische Anfrage", "zh": "医学咨询"},

    # ---------------------------------------------------------------
    # Calculadoras clínicas
    # ---------------------------------------------------------------
    "calc_titulo_vista": {"es": "🧮 Calculadoras clínicas", "en": "🧮 Clinical calculators", "fr": "🧮 Calculatrices cliniques", "de": "🧮 Klinische Rechner", "zh": "🧮 临床计算器"},
    "calc_disclaimer": {
        "es": "Herramientas de apoyo al estudio — no sustituyen la validación clínica de un médico o farmacéutico.",
        "en": "Study support tools — they do not replace clinical validation by a physician or pharmacist.",
        "fr": "Outils d'aide à l'étude — ils ne remplacent pas la validation clinique d'un médecin ou d'un pharmacien.",
        "de": "Werkzeuge zur Unterstützung des Studiums — sie ersetzen nicht die klinische Beurteilung durch einen Arzt oder Apotheker.",
        "zh": "学习辅助工具——不能替代医生或药剂师的临床验证。",
    },
    "campo_peso": {"es": "Peso (kg)", "en": "Weight (kg)", "fr": "Poids (kg)", "de": "Gewicht (kg)", "zh": "体重（kg）"},
    "campo_altura": {"es": "Altura (cm)", "en": "Height (cm)", "fr": "Taille (cm)", "de": "Größe (cm)", "zh": "身高（cm）"},
    "campo_altura_opcional": {"es": "Altura cm (opcional)", "en": "Height cm (optional)", "fr": "Taille cm (optionnel)", "de": "Größe cm (optional)", "zh": "身高 cm（可选）"},
    "campo_edad": {"es": "Edad (años)", "en": "Age (years)", "fr": "Âge (années)", "de": "Alter (Jahre)", "zh": "年龄（岁）"},
    "campo_creatinina": {"es": "Creatinina (mg/dL)", "en": "Creatinine (mg/dL)", "fr": "Créatinine (mg/dL)", "de": "Kreatinin (mg/dL)", "zh": "肌酐（mg/dL）"},
    "campo_sexo": {"es": "Sexo", "en": "Sex", "fr": "Sexe", "de": "Geschlecht", "zh": "性别"},
    "campo_formula": {"es": "Fórmula", "en": "Formula", "fr": "Formule", "de": "Formel", "zh": "公式"},
    "campo_mgkg": {"es": "mg/kg", "en": "mg/kg", "fr": "mg/kg", "de": "mg/kg", "zh": "mg/kg"},
    "campo_dosis_max": {"es": "Dosis máx. mg (opcional)", "en": "Max dose mg (optional)", "fr": "Dose max. mg (optionnel)", "de": "Max. Dosis mg (optional)", "zh": "最大剂量 mg（可选）"},
    "campo_tomas_dia": {"es": "Tomas/día (opcional)", "en": "Doses/day (optional)", "fr": "Prises/jour (optionnel)", "de": "Einnahmen/Tag (optional)", "zh": "每日次数（可选）"},
    "campo_farmaco": {"es": "Fármaco", "en": "Drug", "fr": "Médicament", "de": "Medikament", "zh": "药物"},
    "campo_aclaramiento": {"es": "Aclaramiento (mL/min)", "en": "Clearance (mL/min)", "fr": "Clairance (mL/min)", "de": "Clearance (mL/min)", "zh": "清除率（mL/min）"},
    "campo_farmacos_lista": {
        "es": "Fármacos (uno por línea, mínimo 2)", "en": "Drugs (one per line, minimum 2)", "fr": "Médicaments (un par ligne, minimum 2)",
        "de": "Medikamente (eines pro Zeile, mindestens 2)", "zh": "药物（每行一个，至少 2 个）",
    },
    "usar_peso_ajustado": {
        "es": "Usar peso ajustado (obesidad)", "en": "Use adjusted weight (obesity)", "fr": "Utiliser le poids ajusté (obésité)",
        "de": "Angepasstes Gewicht verwenden (Adipositas)", "zh": "使用校正体重（肥胖）",
    },
    "boton_calcular": {"es": "Calcular", "en": "Calculate", "fr": "Calculer", "de": "Berechnen", "zh": "计算"},
    "boton_buscar_ajuste": {"es": "Buscar ajuste", "en": "Look up adjustment", "fr": "Rechercher l'ajustement", "de": "Anpassung suchen", "zh": "查找调整方案"},
    "boton_verificar_interacciones": {
        "es": "Verificar interacciones", "en": "Check interactions", "fr": "Vérifier les interactions",
        "de": "Wechselwirkungen prüfen", "zh": "检查药物相互作用",
    },

    "panel_imc": {"es": "⚖️ Índice de Masa Corporal (IMC)", "en": "⚖️ Body Mass Index (BMI)", "fr": "⚖️ Indice de Masse Corporelle (IMC)", "de": "⚖️ Body-Mass-Index (BMI)", "zh": "⚖️ 体重指数（BMI）"},
    "panel_bsa": {"es": "📐 Superficie corporal (BSA)", "en": "📐 Body surface area (BSA)", "fr": "📐 Surface corporelle (BSA)", "de": "📐 Körperoberfläche (BSA)", "zh": "📐 体表面积（BSA）"},
    "panel_renal": {
        "es": "🫘 Función renal (aclaramiento de creatinina)",
        "en": "🫘 Renal function (creatinine clearance)",
        "fr": "🫘 Fonction rénale (clairance de la créatinine)",
        "de": "🫘 Nierenfunktion (Kreatinin-Clearance)",
        "zh": "🫘 肾功能（肌酐清除率）",
    },
    "panel_dosis": {"es": "💊 Dosis por peso corporal", "en": "💊 Weight-based dosing", "fr": "💊 Dose selon le poids corporel", "de": "💊 Gewichtsbasierte Dosierung", "zh": "💊 按体重计算剂量"},
    "panel_ajuste_renal": {
        "es": "🧾 Ajuste de dosis por función renal",
        "en": "🧾 Renal dose adjustment",
        "fr": "🧾 Ajustement de dose selon la fonction rénale",
        "de": "🧾 Dosisanpassung nach Nierenfunktion",
        "zh": "🧾 根据肾功能调整剂量",
    },
    "panel_interacciones": {"es": "⚠️ Interacciones farmacológicas", "en": "⚠️ Drug interactions", "fr": "⚠️ Interactions médicamenteuses", "de": "⚠️ Arzneimittelwechselwirkungen", "zh": "⚠️ 药物相互作用"},

    "resultado_imc": {"es": "IMC: {valor} kg/m²", "en": "BMI: {valor} kg/m²", "fr": "IMC : {valor} kg/m²", "de": "BMI: {valor} kg/m²", "zh": "BMI：{valor} kg/m²"},
    "resultado_bsa": {
        "es": "Superficie corporal ({formula}): {valor} m²",
        "en": "Body surface area ({formula}): {valor} m²",
        "fr": "Surface corporelle ({formula}) : {valor} m²",
        "de": "Körperoberfläche ({formula}): {valor} m²",
        "zh": "体表面积（{formula}）：{valor} m²",
    },
    "resultado_cockcroft": {
        "es": "Cockcroft-Gault (para ajustar dosis): {valor} mL/min",
        "en": "Cockcroft-Gault (for dose adjustment): {valor} mL/min",
        "fr": "Cockcroft-Gault (pour ajuster la dose) : {valor} mL/min",
        "de": "Cockcroft-Gault (zur Dosisanpassung): {valor} mL/min",
        "zh": "Cockcroft-Gault（用于调整剂量）：{valor} mL/min",
    },
    "resultado_ckdepi": {
        "es": "CKD-EPI 2021 (para estadificar): {valor} mL/min/1.73m²",
        "en": "CKD-EPI 2021 (for staging): {valor} mL/min/1.73m²",
        "fr": "CKD-EPI 2021 (pour stadifier) : {valor} mL/min/1.73m²",
        "de": "CKD-EPI 2021 (zur Stadieneinteilung): {valor} mL/min/1,73 m²",
        "zh": "CKD-EPI 2021（用于分期）：{valor} mL/min/1.73m²",
    },
    "resultado_dosis_total": {"es": "Dosis total: {valor} mg", "en": "Total dose: {valor} mg", "fr": "Dose totale : {valor} mg", "de": "Gesamtdosis: {valor} mg", "zh": "总剂量：{valor} mg"},
    "aviso_techo_dosis": {
        "es": "⚠️ Se aplicó el techo de dosis máxima indicado.",
        "en": "⚠️ The specified maximum dose ceiling was applied.",
        "fr": "⚠️ Le plafond de dose maximale indiqué a été appliqué.",
        "de": "⚠️ Die angegebene maximale Dosisobergrenze wurde angewendet.",
        "zh": "⚠️ 已应用指定的最大剂量上限。",
    },
    "aviso_piso_dosis": {
        "es": "⚠️ Se aplicó el piso de dosis mínima indicado.",
        "en": "⚠️ The specified minimum dose floor was applied.",
        "fr": "⚠️ Le plancher de dose minimale indiqué a été appliqué.",
        "de": "⚠️ Die angegebene minimale Dosisuntergrenze wurde angewendet.",
        "zh": "⚠️ 已应用指定的最小剂量下限。",
    },
    "dosis_por_toma": {
        "es": "{dosis} mg por toma × {tomas} tomas/día",
        "en": "{dosis} mg per dose × {tomas} doses/day",
        "fr": "{dosis} mg par prise × {tomas} prises/jour",
        "de": "{dosis} mg pro Einnahme × {tomas} Einnahmen/Tag",
        "zh": "每次 {dosis} mg × 每日 {tomas} 次",
    },
    "referencia_educativa": {
        "es": "Referencia educativa — confirma con la ficha técnica vigente.",
        "en": "Educational reference — confirm with the current prescribing information.",
        "fr": "Référence pédagogique — vérifie avec la notice officielle en vigueur.",
        "de": "Pädagogischer Hinweis — bitte mit der aktuellen Fachinformation abgleichen.",
        "zh": "教学参考——请以现行说明书为准。",
    },
    "farmacos_en_tabla": {
        "es": "Fármacos en la tabla de referencia: {lista}",
        "en": "Drugs in the reference table: {lista}",
        "fr": "Médicaments dans le tableau de référence : {lista}",
        "de": "Medikamente in der Referenztabelle: {lista}",
        "zh": "参考表中的药物：{lista}",
    },
    "interacciones_escribe_dos": {
        "es": "Escribe al menos dos fármacos (uno por línea).",
        "en": "Enter at least two drugs (one per line).",
        "fr": "Indique au moins deux médicaments (un par ligne).",
        "de": "Gib mindestens zwei Medikamente ein (eines pro Zeile).",
        "zh": "请至少输入两种药物（每行一个）。",
    },
    "sin_resultados": {"es": "Sin resultados.", "en": "No results.", "fr": "Aucun résultat.", "de": "Keine Ergebnisse.", "zh": "没有结果。"},
    "pares_sin_datos_local": {
        "es": "Pares sin datos en la base local: {pares}",
        "en": "Pairs with no data in the local database: {pares}",
        "fr": "Paires sans données dans la base locale : {pares}",
        "de": "Paare ohne Daten in der lokalen Datenbank: {pares}",
        "zh": "本地数据库中没有数据的药物组合：{pares}",
    },
    "preguntar_ia_sobre": {
        "es": "🤖 Preguntarle a la IA sobre {a} + {b}",
        "en": "🤖 Ask the AI about {a} + {b}",
        "fr": "🤖 Demander à l'IA à propos de {a} + {b}",
        "de": "🤖 Die KI zu {a} + {b} fragen",
        "zh": "🤖 向 AI 询问 {a} + {b}",
    },
    "conocimiento_general_no_verificado": {
        "es": "🤖 Conocimiento general del modelo (NO verificado contra la base curada) — confírmalo con una fuente clínica antes de usarlo:",
        "en": "🤖 General model knowledge (NOT verified against the curated database) — confirm with a clinical source before using it:",
        "fr": "🤖 Connaissance générale du modèle (NON vérifiée par rapport à la base validée) — confirme avec une source clinique avant de l'utiliser :",
        "de": "🤖 Allgemeines Modellwissen (NICHT gegen die kuratierte Datenbank geprüft) — bestätige es mit einer klinischen Quelle, bevor du es verwendest:",
        "zh": "🤖 模型的一般性知识（未与整理过的数据库核实）——使用前请以临床资料确认：",
    },
    "mecanismo": {"es": "Mecanismo: {v}", "en": "Mechanism: {v}", "fr": "Mécanisme : {v}", "de": "Mechanismus: {v}", "zh": "机制：{v}"},
    "efecto": {"es": "Efecto: {v}", "en": "Effect: {v}", "fr": "Effet : {v}", "de": "Wirkung: {v}", "zh": "效应：{v}"},
    "recomendacion": {"es": "Recomendación: {v}", "en": "Recommendation: {v}", "fr": "Recommandation : {v}", "de": "Empfehlung: {v}", "zh": "建议：{v}"},

    # ---------------------------------------------------------------
    # Examen
    # ---------------------------------------------------------------
    "examen_terminado": {"es": "🎓 Examen terminado", "en": "🎓 Exam finished", "fr": "🎓 Examen terminé", "de": "🎓 Prüfung beendet", "zh": "🎓 考试已结束"},
    "aciertos_de": {"es": "Aciertos: {a} de {t}", "en": "Correct: {a} of {t}", "fr": "Bonnes réponses : {a} sur {t}", "de": "Richtig: {a} von {t}", "zh": "正确：{a} / {t}"},
    "pregunta_de": {"es": "Pregunta {n} de {t}", "en": "Question {n} of {t}", "fr": "Question {n} sur {t}", "de": "Frage {n} von {t}", "zh": "第 {n} 题，共 {t} 题"},
    "siguiente": {"es": "Siguiente →", "en": "Next →", "fr": "Suivant →", "de": "Weiter →", "zh": "下一题 →"},
    "salir_del_examen": {"es": "← Salir del examen", "en": "← Exit exam", "fr": "← Quitter l'examen", "de": "← Prüfung verlassen", "zh": "← 退出考试"},
    "escribe_tema_primero": {
        "es": "❌ Escribe un tema en el cuadro de mensaje primero",
        "en": "❌ Type a topic in the message box first",
        "fr": "❌ Écris d'abord un sujet dans la zone de message",
        "de": "❌ Schreibe zuerst ein Thema in das Nachrichtenfeld",
        "zh": "❌ 请先在消息框中输入主题",
    },
    "generando_examen": {"es": "⏳ Generando examen...", "en": "⏳ Generating exam...", "fr": "⏳ Génération de l'examen...", "de": "⏳ Prüfung wird erstellt...", "zh": "⏳ 正在生成考试…"},
    "examen_creado": {
        "es": "✅ {n} preguntas creadas sobre '{tema}'", "en": "✅ {n} questions created about '{tema}'", "fr": "✅ {n} questions créées sur « {tema} »",
        "de": "✅ {n} Fragen zu '{tema}' erstellt", "zh": "✅ 已生成关于“{tema}”的 {n} 道题目",
    },
    "examen_no_generado": {
        "es": "❌ No se pudo generar el examen: {diag}", "en": "❌ Could not generate the exam: {diag}", "fr": "❌ Impossible de générer l'examen : {diag}",
        "de": "❌ Die Prüfung konnte nicht erstellt werden: {diag}", "zh": "❌ 无法生成考试：{diag}",
    },
    "tus_documentos": {"es": "Tus documentos", "en": "Your documents", "fr": "Tes documents", "de": "Deine Dokumente", "zh": "你的文档"},
    "conocimiento_general": {"es": "Conocimiento general", "en": "General knowledge", "fr": "Connaissances générales", "de": "Allgemeinwissen", "zh": "通用知识"},

    # ---------------------------------------------------------------
    # Flashcards / repaso
    # ---------------------------------------------------------------
    "repaso_terminado": {"es": "🎉 Terminaste el repaso de hoy.", "en": "🎉 You finished today's review.", "fr": "🎉 Tu as terminé la révision du jour.", "de": "🎉 Du hast die heutige Wiederholung beendet.", "zh": "🎉 你已完成今天的复习。"},
    "sin_flashcards_pendientes": {
        "es": "🎉 No tienes flashcards pendientes por hoy.",
        "en": "🎉 You have no flashcards pending today.",
        "fr": "🎉 Tu n'as aucune carte à réviser aujourd'hui.",
        "de": "🎉 Du hast heute keine ausstehenden Karteikarten.",
        "zh": "🎉 你今天没有待复习的记忆卡。",
    },
    "tarjeta_de": {"es": "Tarjeta {n} de {t}", "en": "Card {n} of {t}", "fr": "Carte {n} sur {t}", "de": "Karte {n} von {t}", "zh": "第 {n} 张，共 {t} 张"},
    "boton_otra_vez": {"es": "Otra vez", "en": "Again", "fr": "Encore", "de": "Nochmal", "zh": "重来"},
    "boton_dificil": {"es": "Difícil", "en": "Hard", "fr": "Difficile", "de": "Schwer", "zh": "困难"},
    "boton_bien": {"es": "Bien", "en": "Good", "fr": "Bien", "de": "Gut", "zh": "良好"},
    "boton_facil": {"es": "Fácil", "en": "Easy", "fr": "Facile", "de": "Leicht", "zh": "简单"},
    "mostrar_respuesta": {"es": "Mostrar respuesta", "en": "Show answer", "fr": "Afficher la réponse", "de": "Antwort anzeigen", "zh": "显示答案"},
    "salir_del_repaso": {"es": "← Salir del repaso", "en": "← Exit review", "fr": "← Quitter la révision", "de": "← Wiederholung verlassen", "zh": "← 退出复习"},
    "generando_flashcards": {"es": "⏳ Generando flashcards...", "en": "⏳ Generating flashcards...", "fr": "⏳ Génération des cartes...", "de": "⏳ Karteikarten werden erstellt...", "zh": "⏳ 正在生成记忆卡…"},
    "flashcards_creadas": {
        "es": "✅ {n} flashcards creadas sobre '{tema}'", "en": "✅ {n} flashcards created about '{tema}'", "fr": "✅ {n} cartes créées sur « {tema} »",
        "de": "✅ {n} Karteikarten zu '{tema}' erstellt", "zh": "✅ 已生成关于“{tema}”的 {n} 张记忆卡",
    },
    "flashcards_no_generadas": {
        "es": "❌ No se pudieron generar flashcards: {diag}",
        "en": "❌ Could not generate flashcards: {diag}",
        "fr": "❌ Impossible de générer les cartes : {diag}",
        "de": "❌ Karteikarten konnten nicht erstellt werden: {diag}",
        "zh": "❌ 无法生成记忆卡：{diag}",
    },
    "esto_se_relaciona_con": {
        "es": "🧠 Esto se relaciona con lo que ya estudiaste: {temas}",
        "en": "🧠 This relates to what you already studied: {temas}",
        "fr": "🧠 Cela est lié à ce que tu as déjà étudié : {temas}",
        "de": "🧠 Das hängt mit dem zusammen, was du bereits gelernt hast: {temas}",
        "zh": "🧠 这与你之前学过的内容有关：{temas}",
    },

    # ---------------------------------------------------------------
    # Progreso
    # ---------------------------------------------------------------
    "progreso_titulo": {"es": "📊 Tu progreso de estudio", "en": "📊 Your study progress", "fr": "📊 Ta progression d'étude", "de": "📊 Dein Lernfortschritt", "zh": "📊 你的学习进度"},
    "temas_estudiados": {"es": "{n} temas estudiados", "en": "{n} topics studied", "fr": "{n} sujets étudiés", "de": "{n} gelernte Themen", "zh": "已学习 {n} 个主题"},
    "n_flashcards": {"es": "{n} flashcards", "en": "{n} flashcards", "fr": "{n} cartes mémo", "de": "{n} Karteikarten", "zh": "{n} 张记忆卡"},
    "n_preguntas_examen": {"es": "{n} preguntas de examen", "en": "{n} exam questions", "fr": "{n} questions d'examen", "de": "{n} Prüfungsfragen", "zh": "{n} 道考试题"},
    "n_intentos_respondidos": {"es": "{n} intentos respondidos", "en": "{n} attempts answered", "fr": "{n} tentatives répondues", "de": "{n} beantwortete Versuche", "zh": "已完成 {n} 次作答"},
    "sin_examenes_suficientes": {
        "es": "Todavía no tienes suficientes exámenes respondidos para evaluar tu nivel por tema. Genera y responde algunos exámenes para que esto se llene.",
        "en": "You don't have enough answered exams yet to evaluate your level per topic. Generate and answer some exams to fill this in.",
        "fr": "Tu n'as pas encore assez d'examens répondus pour évaluer ton niveau par sujet. Génère et réponds à quelques examens pour remplir cette section.",
        "de": "Du hast noch nicht genug beantwortete Prüfungen, um dein Niveau pro Thema zu bewerten. Erstelle und beantworte ein paar Prüfungen, damit sich das hier füllt.",
        "zh": "你回答的考试还不够多，无法评估你在各主题上的水平。生成并完成一些考试，这里就会显示相应内容。",
    },
    "nivel_por_tema": {
        "es": "Nivel por tema (según tus exámenes respondidos):",
        "en": "Level per topic (based on your answered exams):",
        "fr": "Niveau par sujet (selon tes examens répondus) :",
        "de": "Niveau pro Thema (basierend auf deinen beantworteten Prüfungen):",
        "zh": "各主题水平（根据你已完成的考试）：",
    },
    "correctas_pct": {
        "es": "{a}/{t} correctas ({p}%)", "en": "{a}/{t} correct ({p}%)", "fr": "{a}/{t} correctes ({p}%)",
        "de": "{a}/{t} richtig ({p}%)", "zh": "{a}/{t} 正确（{p}%）",
    },
    "nivel_necesita_repaso": {"es": "Necesita repaso", "en": "Needs review", "fr": "À revoir", "de": "Braucht Wiederholung", "zh": "需要复习"},
    "nivel_en_progreso": {"es": "En progreso", "en": "In progress", "fr": "En cours", "de": "In Bearbeitung", "zh": "进行中"},
    "nivel_dominado": {"es": "Dominado", "en": "Mastered", "fr": "Maîtrisé", "de": "Beherrscht", "zh": "已掌握"},
    "nivel_pocos_datos": {"es": "Muy pocos datos aún", "en": "Not enough data yet", "fr": "Pas encore assez de données", "de": "Noch zu wenige Daten", "zh": "数据还太少"},

    # ---------------------------------------------------------------
    # Categorías clínicas devueltas por calculadoras_clinicas.py — son
    # un vocabulario fijo y pequeño (a diferencia de la base de
    # interacciones, que es texto libre extenso), así que sí vale la
    # pena traducirlas aquí en vez de dejarlas siempre en español.
    # ---------------------------------------------------------------
    "cat_bajo_peso": {"es": "Bajo peso", "en": "Underweight", "fr": "Insuffisance pondérale", "de": "Untergewicht", "zh": "体重过轻"},
    "cat_peso_normal": {"es": "Peso normal", "en": "Normal weight", "fr": "Poids normal", "de": "Normalgewicht", "zh": "体重正常"},
    "cat_sobrepeso": {"es": "Sobrepeso", "en": "Overweight", "fr": "Surpoids", "de": "Übergewicht", "zh": "超重"},
    "cat_obesidad_1": {"es": "Obesidad grado I", "en": "Obesity class I", "fr": "Obésité de classe I", "de": "Adipositas Grad I", "zh": "I 度肥胖"},
    "cat_obesidad_2": {"es": "Obesidad grado II", "en": "Obesity class II", "fr": "Obésité de classe II", "de": "Adipositas Grad II", "zh": "II 度肥胖"},
    "cat_obesidad_3": {"es": "Obesidad grado III", "en": "Obesity class III", "fr": "Obésité de classe III", "de": "Adipositas Grad III", "zh": "III 度肥胖"},
    "cat_renal_normal": {"es": "Función renal normal", "en": "Normal renal function", "fr": "Fonction rénale normale", "de": "Normale Nierenfunktion", "zh": "肾功能正常"},
    "cat_renal_leve": {"es": "Insuficiencia renal leve", "en": "Mild renal impairment", "fr": "Insuffisance rénale légère", "de": "Leichte Niereninsuffizienz", "zh": "轻度肾功能不全"},
    "cat_renal_moderada": {"es": "Insuficiencia renal moderada", "en": "Moderate renal impairment", "fr": "Insuffisance rénale modérée", "de": "Mäßige Niereninsuffizienz", "zh": "中度肾功能不全"},
    "cat_renal_grave": {"es": "Insuficiencia renal grave", "en": "Severe renal impairment", "fr": "Insuffisance rénale sévère", "de": "Schwere Niereninsuffizienz", "zh": "重度肾功能不全"},
    "cat_renal_fallo": {"es": "Fallo renal", "en": "Renal failure", "fr": "Insuffisance rénale terminale", "de": "Nierenversagen", "zh": "肾衰竭"},
    "cat_ckd_g1": {"es": "G1 (normal o alta)", "en": "G1 (normal or high)", "fr": "G1 (normale ou élevée)", "de": "G1 (normal oder hoch)", "zh": "G1（正常或偏高）"},
    "cat_ckd_g2": {"es": "G2 (levemente disminuida)", "en": "G2 (mildly decreased)", "fr": "G2 (légèrement diminuée)", "de": "G2 (leicht vermindert)", "zh": "G2（轻度下降）"},
    "cat_ckd_g3a": {"es": "G3a (leve a moderadamente disminuida)", "en": "G3a (mildly to moderately decreased)", "fr": "G3a (légèrement à modérément diminuée)", "de": "G3a (leicht bis mäßig vermindert)", "zh": "G3a（轻至中度下降）"},
    "cat_ckd_g3b": {"es": "G3b (moderada a gravemente disminuida)", "en": "G3b (moderately to severely decreased)", "fr": "G3b (modérément à sévèrement diminuée)", "de": "G3b (mäßig bis stark vermindert)", "zh": "G3b（中至重度下降）"},
    "cat_ckd_g4": {"es": "G4 (gravemente disminuida)", "en": "G4 (severely decreased)", "fr": "G4 (sévèrement diminuée)", "de": "G4 (stark vermindert)", "zh": "G4（重度下降）"},
    "cat_ckd_g5": {"es": "G5 (fallo renal)", "en": "G5 (kidney failure)", "fr": "G5 (insuffisance rénale terminale)", "de": "G5 (Nierenversagen)", "zh": "G5（肾衰竭）"},
}


# Traduce una categoría clínica devuelta por calculadoras_clinicas.py
# (siempre viene en español desde ese módulo — es más simple traducir
# aquí, en un solo lugar, que duplicar la lógica de clasificación en 5
# idiomas dentro de cada función de cálculo).
_MAPA_CATEGORIAS = {
    "Bajo peso": "cat_bajo_peso", "Peso normal": "cat_peso_normal", "Sobrepeso": "cat_sobrepeso",
    "Obesidad grado I": "cat_obesidad_1", "Obesidad grado II": "cat_obesidad_2", "Obesidad grado III": "cat_obesidad_3",
    "Función renal normal": "cat_renal_normal", "Insuficiencia renal leve": "cat_renal_leve",
    "Insuficiencia renal moderada": "cat_renal_moderada", "Insuficiencia renal grave": "cat_renal_grave",
    "Fallo renal": "cat_renal_fallo",
    "G1 (normal o alta)": "cat_ckd_g1", "G2 (levemente disminuida)": "cat_ckd_g2",
    "G3a (leve a moderadamente disminuida)": "cat_ckd_g3a", "G3b (moderada a gravemente disminuida)": "cat_ckd_g3b",
    "G4 (gravemente disminuida)": "cat_ckd_g4", "G5 (fallo renal)": "cat_ckd_g5",
    # Niveles de jerarquía de evidencia (pubmed_search.py: _ORDEN_JERARQUIA_EVIDENCIA)
    "Revisión (meta-análisis)": "niv_meta_analisis",
    "Revisión (sistemática)": "niv_revision_sistematica",
    "Guía clínica": "niv_guia_clinica",
    "Evidencia primaria (ensayo clínico aleatorizado)": "niv_ensayo_aleatorizado",
    "Evidencia primaria (ensayo clínico)": "niv_ensayo_clinico",
    "Evidencia primaria (observacional)": "niv_observacional",
    "Evidencia primaria (reporte de caso)": "niv_reporte_caso",
    "Revisión (narrativa)": "niv_revision_narrativa",
    "Opinión/comentario": "niv_opinion",
    "Preprint (sin revisión por pares)": "niv_preprint",
    "Sin clasificar": "niv_sin_clasificar",
}


def t_categoria(categoria_es: str, idioma: str = "es") -> str:
    """
    Traduce una categoría clínica (string fijo devuelto por
    calculadoras_clinicas.py, siempre en español) al idioma pedido.
    Si la categoría no está en el mapa (no debería pasar salvo que se
    agregue una categoría nueva al módulo de cálculo y se olvide
    registrarla aquí), la devuelve tal cual en vez de fallar.
    """
    clave = _MAPA_CATEGORIAS.get(categoria_es)
    if not clave:
        return categoria_es
    return t(clave, idioma)


def t(clave: str, idioma: str = "es", **kwargs) -> str:
    """
    Devuelve el texto de `clave` en `idioma`. Si faltara la clave o el
    idioma, cae a español y, si tampoco existe, devuelve la clave entre
    corchetes (nunca una cadena vacía ni una excepción) — así un texto
    sin traducir se nota de inmediato en la UI en vez de desaparecer.

    kwargs permite interpolar valores con .format(), ej.:
    t("repasar", "en", n=3) -> "📇 Review (3 pending)"
    """
    entrada = TEXTOS.get(clave)
    if not entrada:
        return f"[{clave}]"
    texto = entrada.get(idioma) or entrada.get("es") or f"[{clave}]"
    if kwargs:
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto
    return texto
