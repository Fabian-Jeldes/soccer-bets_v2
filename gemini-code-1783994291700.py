import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# Configuración del documento
pdf_path = "investigacion_apuestas_futbol.pdf"
doc = SimpleDocTemplate(
    pdf_path,
    pagesize=letter,
    leftMargin=54,  # 0.75 in
    rightMargin=54,
    topMargin=54,
    bottomMargin=54
)

styles = getSampleStyleSheet()

# Colores de la paleta corporativa
primary_color = colors.HexColor("#1A365D")  # Azul oscuro
secondary_color = colors.HexColor("#0D9488")  # Turquesa/Teal
text_color = colors.HexColor("#1F2937")  # Gris carbón
accent_color = colors.HexColor("#2563EB")  # Azul brillante

# Estilos personalizados
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=22,
    leading=26,
    textColor=primary_color,
    alignment=TA_CENTER,
    spaceAfter=15
)

subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=12,
    leading=16,
    textColor=colors.HexColor("#4B5563"),
    alignment=TA_CENTER,
    spaceAfter=30
)

h1_style = ParagraphStyle(
    'SectionH1',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=14,
    leading=18,
    textColor=primary_color,
    spaceBefore=18,
    spaceAfter=8,
    keepWithNext=True
)

body_style = ParagraphStyle(
    'DocBody',
    parent=styles['BodyText'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=text_color,
    spaceAfter=8,
    alignment=TA_JUSTIFY
)

table_header_style = ParagraphStyle(
    'TableHeader',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=8,
    leading=10,
    textColor=colors.white,
    alignment=TA_LEFT
)

table_body_style = ParagraphStyle(
    'TableBody',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=7.5,
    leading=10,
    textColor=text_color,
    alignment=TA_LEFT
)

code_style = ParagraphStyle(
    'CodeStyle',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#1F2937"),
    backColor=colors.HexColor("#F3F4F6"),
    borderColor=colors.HexColor("#E5E7EB"),
    borderWidth=1,
    borderPadding=8,
    spaceBefore=8,
    spaceAfter=8
)

story = []

# --- PORTADA ---
story.append(Spacer(1, 40))
story.append(Paragraph("SISTEMA DE PREDICCIÓN Y ARBITRAJE DE APUESTAS DE FÚTBOL EN TIEMPO REAL", title_style))
story.append(Paragraph("Análisis Geoestructural de Ligas Emergentes y Arquitectura de Datos de Alta Frecuencia", subtitle_style))
story.append(Spacer(1, 20))

meta_text = """
<b>Autor:</b> Gemini (Google Deep Research)<br/>
<b>Destinatario:</b> Equipo de Desarrollo de Software y Sistemas Algorítmicos<br/>
<b>Fecha de Generación:</b> Julio 2026<br/>
<b>Estado:</b> Documento de Especificación Técnica Completo<br/>
"""
story.append(Paragraph(meta_text, ParagraphStyle('Meta', parent=body_style, alignment=TA_CENTER, textColor=colors.HexColor("#374151"))))
story.append(Spacer(1, 40))

intro_text = (
    "El presente informe constituye una investigación exhaustiva y multidimensional para el "
    "diseño y construcción de una plataforma algorítmica orientada a la predicción deportiva "
    "y a la captura de ineficiencias de mercado mediante arbitraje financiero (surebets). "
    "A lo largo de este documento, se validan hipótesis relativas a ligas de menor categoría en África y Asia, "
    "se analizan las fuentes de datos históricos y en vivo, y se propone una arquitectura robusta de alto "
    "rendimiento en React, WebSockets y Redis 8."
)
story.append(Paragraph(intro_text, body_style))
story.append(PageBreak())

# --- SECCIÓN 1 ---
story.append(Paragraph("1. Fundamentos del Modelado Dual: Predicción de Valor vs. Arbitraje Financiero", h1_style))
p1 = (
    "En el ámbito de los mercados de apuestas de fútbol, coexisten dos metodologías analíticas fundamentales pero operativamente opuestas: "
    "el modelado predictivo de valor y el arbitraje financiero o <i>surebet</i>. Comprender la divergencia conceptual y la complementariedad "
    "de ambas es el primer paso para estructurar un sistema comercialmente viable.<br/><br/>"
    "La <b>modelación predictiva</b> busca determinar la probabilidad matemática real de un resultado específico y compararla con la "
    "probabilidad implícita en las cuotas ofrecidas por los operadores. Si el modelo predictivo estima que un equipo local tiene un 75% "
    "de probabilidad de ganar un partido, lo que equivale a una cuota justa de 1.33, y el mercado la ofrece a 1.50 (probabilidad implícita "
    "del 66.6%), el sistema identifica una apuesta de valor positivo (+EV). Este enfoque se basa en la acumulación de ventajas estadísticas "
    "a largo plazo y asume el riesgo inherente a la varianza deportiva.<br/><br/>"
    "Por el contrario, el <b>arbitraje de apuestas</b> no intenta predecir el resultado deportivo de un evento. Su objetivo es puramente "
    "financiero: explotar las discrepancias temporales de precios entre dos o más casas de apuestas competidoras que han tasado de manera "
    "asimétrica los lados opuestos de un mismo mercado. Al realizar apuestas simultáneas y proporcionales en todos los resultados posibles "
    "a través de diferentes plataformas, el sistema elimina por completo el riesgo deportivo, asegurando un retorno de capital inmediato "
    "sin importar cuál sea el desenlace del partido.<br/><br/>"
    "La sinergia de ambos enfoques dentro de una misma plataforma web permite diversificar el riesgo: mientras que el módulo de arbitraje "
    "proporciona un flujo constante de ganancias de bajo riesgo para la capitalización del sistema, el módulo predictivo optimiza las "
    "recomendaciones en mercados secundarios de baja liquidez donde las ventanas de arbitraje son estrechas pero las ineficiencias de las "
    "cuotas locales son masivas."
)
story.append(Paragraph(p1, body_style))

# --- SECCIÓN 2 ---
story.append(Paragraph("2. Análisis de Datasets Históricos y Registros de Apuestas", h1_style))
p2 = (
    "Para entrenar modelos de aprendizaje automático y validar estrategias de arbitraje, es indispensable contar con repositorios de "
    "datos históricos que abaquen tanto el rendimiento deportivo de los equipos como la evolución y cierre de las líneas de apuestas. "
    "El análisis de los datos debe ir más allá de la mera recopilación de resultados finales para profundizar en el registro de las "
    "transacciones de apuestas y las dinámicas de cuotas de apertura y cierre."
)
story.append(Paragraph(p2, body_style))

table_data_1 = [
    [
        Paragraph("<b>Dataset / Proveedor</b>", table_header_style),
        Paragraph("<b>Amplitud Temporal</b>", table_header_style),
        Paragraph("<b>Cobertura de Ligas</b>", table_header_style),
        Paragraph("<b>Variables de Apuestas</b>", table_header_style),
        Paragraph("<b>Variables Deportivas</b>", table_header_style),
        Paragraph("<b>Usos Principales</b>", table_header_style)
    ],
    [
        Paragraph("Kaggle European Soccer", table_body_style),
        Paragraph("30 temporadas (1993-2023)", table_body_style),
        Paragraph("22 divisiones europeas, incl. ligas menores", table_body_style),
        Paragraph("Cuotas históricas Bet365, Blue Sq, BWin (1X2)", table_body_style),
        Paragraph("Marcadores, tiros, córners, tarjetas, faltas", table_body_style),
        Paragraph("Entrenamiento de modelos de valor, Poisson", table_body_style)
    ],
    [
        Paragraph("TheStatsAPI", table_body_style),
        Paragraph("10 años de profundidad", table_body_style),
        Paragraph("150 por defecto; hasta 1,196 bajo demanda (Asia/África)", table_body_style),
        Paragraph("Cuotas prematch e in-play de Pinnacle, Bet365, Betfair", table_body_style),
        Paragraph("Estadísticas de 84k+ jugadores, eventos en vivo, xG", table_body_style),
        Paragraph("Backtesting de modelos basados en xG y rendimiento", table_body_style)
    ],
    [
        Paragraph("Footiqo Database", table_body_style),
        Paragraph("Temporadas recientes y en curso", table_body_style),
        Paragraph("Cobertura global de ligas principales y secundarias", table_body_style),
        Paragraph("Cuotas históricas de cierre provistas por 1xBet", table_body_style),
        Paragraph("Resultados finales, Over/Under, Ambos Anotan", table_body_style),
        Paragraph("Validación de modelos de mercados secundarios", table_body_style)
    ],
    [
        Paragraph("SportsDataIO Historical", table_body_style),
        Paragraph("Desde 2019 (props desde 2020)", table_body_style),
        Paragraph("Cobertura multideportiva con enfoque global", table_body_style),
        Paragraph("Cuotas estructuradas prematch, in-play y props", table_body_style),
        Paragraph("Estadísticas agregadas, calendarios, lesiones", table_body_style),
        Paragraph("Modelos de redes neuronales de proposiciones complejas", table_body_style)
    ],
    [
        Paragraph("Notbet Proprietary", table_body_style),
        Paragraph("Historial multianual continuo", table_body_style),
        Paragraph("Más de 3 millones de partidos de fútbol", table_body_style),
        Paragraph("Cuotas minuto a minuto y ticks de fluctuación", table_body_style),
        Paragraph("Incidencias desglosadas por intervalos de un minuto", table_body_style),
        Paragraph("Identificación de ineficiencias de mercado en vivo", table_body_style)
    ]
]

col_widths_1 = [80, 70, 95, 95, 95, 95]
t1 = Table(table_data_1, colWidths=col_widths_1)
t1.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), primary_color),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('BOTTOMPADDING', (0,0), (-1,0), 6),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))

story.append(t1)
story.append(Spacer(1, 10))
p2_sub = (
    "El análisis de la rentabilidad requiere simular dinámicas reales. Es crucial registrar el estado "
    "detallado de la liquidación (v.g., Won, Lost, Refunded, Half Won, Half Lost) en mercados como "
    "Hándicap Asiático. Almacenar el timestamp de cada movimiento de cuotas permite correlacionar el flujo de "
    "dinero inteligente (v.g., analizando casas como Pinnacle) para ajustar las predicciones in-play."
)
story.append(Paragraph(p2_sub, body_style))
story.append(PageBreak())

# --- SECCIÓN 3 ---
story.append(Paragraph("3. Cuantificación de la Ventaja de Localía en Ligas Menores de África y Asia", h1_style))
p3 = (
    "La hipótesis sobre la existencia de ligas de menor categoría en África o Asia con una ventaja de localía extrema "
    "está respaldada por la investigación científica en ciencias del deporte. En estas ligas, jugar en casa representa una ventaja "
    "desproporcionada en comparación con los estándares de las ligas europeas de élite.<br/><br/>"
    "Para evaluar matemáticamente la ventaja de localía de una liga, la probabilidad normalizada de victoria local (<i>hProb</i>) se "
    "deduce de las cuotas decimales medias de victoria local ($O_H$), empate ($O_D$) y victoria visitante ($O_A$):<br/>"
)
story.append(Paragraph(p3, body_style))

eq1 = Paragraph("<b><i>hProb = (1 / O_H) / [ (1 / O_H) + (1 / O_D) + (1 / O_A) ]</i></b>", ParagraphStyle('Eq', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq1)
story.append(Spacer(1, 5))

p3_2 = (
    "De forma equivalente, al analizar los puntos acumulados al final de una temporada, la ventaja de localía se "
    "calcula como el porcentaje de puntos totales ganados por los equipos locales respecto al total de puntos disputados:<br/>"
)
story.append(Paragraph(p3_2, body_style))

eq2 = Paragraph("<b><i>Ventaja Localía % = (Puntos Obtenidos en Casa / Puntos Totales Obtenidos) * 100</i></b>", ParagraphStyle('Eq2', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq2)
story.append(Spacer(1, 10))

p3_3 = (
    "Estudios empíricos demuestran que en condiciones de paridad este valor converge al 50%. Sin embargo, en ligas en desarrollo se observan desviaciones "
    "extremas debidas a factores geoestructurales y sociopolíticos clave:<br/>"
    "• <b>Fatiga por viajes e infraestructura:</b> En países extensos o con transporte terrestre deficiente, los equipos visitantes experimentan trayectos agotadores que merman su rendimiento.<br/>"
    "• <b>Presión de la afición y sesgo arbitral:</b> La presión psicológica sobre los jugadores y la influencia inconsciente o forzada sobre las decisiones de los árbitros son más pronunciadas en ligas con menores garantías de seguridad.<br/>"
    "• <b>Asimetrías geográficas y de altitud:</b> El juego en altitudes extremas o climas tropicales severos ejerce un impacto fisiológico adverso en equipos no adaptados.<br/>"
    "• <b>Corrupción y debilidad institucional:</b> Existe una fuerte correlación estadística entre los índices de percepción de corrupción nacionales y una ventaja de localía inusualmente alta en ligas de ascenso y divisiones inferiores."
)
story.append(Paragraph(p3_3, body_style))
story.append(Spacer(1, 5))

table_data_2 = [
    [
        Paragraph("<b>Variable</b>", table_header_style),
        Paragraph("<b>Comportamiento Estadístico</b>", table_header_style),
        Paragraph("<b>Implicación para el Modelo</b>", table_header_style),
        Paragraph("<b>Coeficiente / Influencia</b>", table_header_style)
    ],
    [
        Paragraph("Goles anotados", table_body_style),
        Paragraph("Significativamente más altos en casa (p < 0.001)", table_body_style),
        Paragraph("Aumenta expectativa de goles locales en modelo Poisson", table_body_style),
        Paragraph("Coeficiente de localía ~0.3 (1.35 veces más goles)", table_body_style)
    ],
    [
        Paragraph("Asistencias y pases clave", table_body_style),
        Paragraph("Mayor volumen y tasa de éxito en el tercio ofensivo", table_body_style),
        Paragraph("Equipo local asume postura predominantemente ofensiva", table_body_style),
        Paragraph("Fuerte predictor de dominio táctico local", table_body_style)
    ],
    [
        Paragraph("Faltas cometidas", table_body_style),
        Paragraph("Defensores cometen menos faltas en casa (p=0.005)", table_body_style),
        Paragraph("Sesgo defensivo visitante; mayor probabilidad de tarjetas", table_body_style),
        Paragraph("Aumento de cuota de tarjetas para el visitante", table_body_style)
    ],
    [
        Paragraph("Ausencia de público (COVID)", table_body_style),
        Paragraph("Desvanecimiento significativo de la ventaja tradicional", table_body_style),
        Paragraph("Demuestra influencia causal directa del público en árbitros", table_body_style),
        Paragraph("Ajuste a la baja en partidos a puerta cerrada o neutrales", table_body_style)
    ]
]

col_widths_2 = [100, 150, 150, 130]
t2 = Table(table_data_2, colWidths=col_widths_2)
t2.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), primary_color),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(t2)
story.append(PageBreak())

# --- SECCIÓN 4 ---
story.append(Paragraph("4. Mecánica de Ejecución del Arbitraje de Apuestas (Surebets)", h1_style))
p4 = (
    "El arbitraje de apuestas consiste en identificar cuotas en diferentes operadores para un mismo evento que, al ser combinadas, "
    "garantizan un retorno libre de riesgo deportivo. Para un mercado de dos opciones, el porcentaje de arbitraje se calcula como:<br/>"
)
story.append(Paragraph(p4, body_style))

eq3 = Paragraph("<b><i>Arb % = (1 / O_1) + (1 / O_2)</i></b>", ParagraphStyle('Eq3', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq3)
story.append(Spacer(1, 5))

p4_2 = (
    "Si el valor de Arb % es estrictamente menor a 1.00 (100%), existe una oportunidad de arbitraje. Las sumas a apostar para un presupuesto "
    "total <i>B</i> se determinan como:<br/>"
)
story.append(Paragraph(p4_2, body_style))

eq4 = Paragraph("<b><i>Apuesta_i = [ B * (1 / O_i) ] / Arb %</i></b>", ParagraphStyle('Eq4', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq4)
story.append(Spacer(1, 5))

p4_3 = (
    "Para mercados de tres vías (1X2) la fórmula se expande sumando 1/O_H + 1/O_D + 1/O_A. <br/>"
    "<b>Arbitraje Cruzado con Plataformas de Predicción (v.g. Polymarket, Kalshi):</b><br/>"
    "En estas plataformas los contratos se negocian en centavos (0-100¢). Para convertirlos a cuotas decimales equivalentes se utiliza:<br/>"
)
story.append(Paragraph(p4_3, body_style))

eq5 = Paragraph("<b><i>Cuota Decimal Equivalente (O_d) = 1 / (Precio del Contrato en centavos / 100)</i></b>", ParagraphStyle('Eq5', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq5)
story.append(Spacer(1, 5))

p4_4 = (
    "Si la plataforma cobra una comisión fija <i>f</i> sobre las ganancias netas del contrato, la cuota decimal efectiva real se calcula mediante:<br/>"
)
story.append(Paragraph(p4_4, body_style))

eq6 = Paragraph("<b><i>O_efectiva = 1 + (O_d - 1) * (1 - f)</i></b>", ParagraphStyle('Eq6', parent=body_style, alignment=TA_CENTER, fontName='Helvetica-BoldOblique', textColor=accent_color))
story.append(eq6)
story.append(Spacer(1, 10))

table_data_3 = [
    [
        Paragraph("<b>Resultado</b>", table_header_style),
        Paragraph("<b>Casa Seleccionada</b>", table_header_style),
        Paragraph("<b>Cuota (O_i)</b>", table_header_style),
        Paragraph("<b>Prob. Implícita</b>", table_header_style),
        Paragraph("<b>Apuesta Teórica ($1k)</b>", table_header_style),
        Paragraph("<b>Apuesta Redondeada</b>", table_header_style),
        Paragraph("<b>Retorno Bruto</b>", table_header_style),
        Paragraph("<b>Ganancia Neta</b>", table_header_style)
    ],
    [
        Paragraph("Victoria Local (1)", table_body_style),
        Paragraph("Bookie A (Soft)", table_body_style),
        Paragraph("2.80", table_body_style),
        Paragraph("35.71%", table_body_style),
        Paragraph("$365.17", table_body_style),
        Paragraph("<b>$365.00</b>", table_body_style),
        Paragraph("$1,022.00", table_body_style),
        Paragraph("<b>$22.00 (2.20%)</b>", table_body_style)
    ],
    [
        Paragraph("Empate (X)", table_body_style),
        Paragraph("Bookie B (Sharp)", table_body_style),
        Paragraph("3.50", table_body_style),
        Paragraph("28.57%", table_body_style),
        Paragraph("$292.14", table_body_style),
        Paragraph("<b>$292.00</b>", table_body_style),
        Paragraph("$1,022.00", table_body_style),
        Paragraph("<b>$22.00 (2.20%)</b>", table_body_style)
    ],
    [
        Paragraph("Victoria Visitante (2)", table_body_style),
        Paragraph("Bookie C (Exchange)", table_body_style),
        Paragraph("3.00", table_body_style),
        Paragraph("33.33%", table_body_style),
        Paragraph("$342.69", table_body_style),
        Paragraph("<b>$343.00</b>", table_body_style),
        Paragraph("$1,029.00", table_body_style),
        Paragraph("<b>$29.00 (2.90%)</b>", table_body_style)
    ],
    [
        Paragraph("<b>Totales</b>", table_body_style),
        Paragraph("<b>Multiorigen</b>", table_body_style),
        Paragraph("<b>Arb% = 97.61%</b>", table_body_style),
        Paragraph("<b>Suma = 0.9761</b>", table_body_style),
        Paragraph("<b>$1,000.00</b>", table_body_style),
        Paragraph("<b>$1,000.00</b>", table_body_style),
        Paragraph("<b>Mín. $1,022.00</b>", table_body_style),
        Paragraph("<b>Mín. $22.00</b>", table_body_style)
    ]
]

col_widths_3 = [80, 80, 50, 60, 85, 85, 65, 65]
t3 = Table(table_data_3, colWidths=col_widths_3)
t3.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), primary_color),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
    ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#F8FAFC")]),
    ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E2E8F0")),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(t3)
story.append(Spacer(1, 10))
p4_5 = (
    "<b>Evasión de Bloqueos mediante Redondeo:</b> Las casas de apuestas recreativas bloquean o limitan las cuentas que "
    "apuestan montos con decimales exactos (v.g. $365.17) porque delatan el uso de softwares de arbitraje. El redondeo a enteros "
    "($365.00) mimetiza el comportamiento recreativo y extiende enormemente la vida útil de las cuentas."
)
story.append(Paragraph(p4_5, body_style))
story.append(PageBreak())

# --- SECCIÓN 5 ---
story.append(Paragraph("5. Estrategia de Raspado, Ingesta de Datos y Correspondencia de Nombres", h1_style))
p5 = (
    "Para capturar las cuotas en vivo, la arquitectura debe implementar un motor de ingesta avanzada capaz de evadir cortafuegos "
    "perimetrales y normalizar las identidades de los equipos deportivos provenientes de distintas fuentes.<br/><br/>"
    "<b>Canalización de Raspado con Playwright y APIs Ocultas:</b><br/>"
    "1. <i>APIs Ocultas:</i> Se inspecciona el tráfico de red de un navegador para extraer los endpoints internos JSON de los operadores, "
    "evitando renderizar HTML pesado.<br/>"
    "2. <i>OddsHarvester (Playwright):</i> En entornos con cifrado de firmas dinámicas, se automatiza un navegador. Se utiliza el modo "
    "<code>--preview-only</code> para descargar solo cuotas agregadas sin interactuar con cada página de partido, optimizando el ancho de "
    "banda y CPU. Se rotan proxies residenciales y se simula la geolocalización, huso horario y idioma alineado a la IP para evadir sistemas anti-bot.<br/><br/>"
    "<b>Problema de Correspondencia Difusa de Equipos (Fuzzy Name Matching):</b><br/>"
    "Dado que los operadores nombran los equipos de manera diferente (ej. 'Man Utd' vs 'Manchester United FC'), se aplica una tubería de correspondencia difusa:"
)
story.append(Paragraph(p5, body_style))

table_data_4 = [
    [
        Paragraph("<b>Método</b>", table_header_style),
        Paragraph("<b>Algoritmo y Mecanismo</b>", table_header_style),
        Paragraph("<b>Ventajas Clave</b>", table_header_style),
        Paragraph("<b>Caso de Uso Óptimo</b>", table_header_style)
    ],
    [
        Paragraph("Distancia de Edición Relativa", table_body_style),
        Paragraph("Levenshtein Distance / RapidFuzz: Mide operaciones de edición de caracteres", table_body_style),
        Paragraph("Excelente para errores ortográficos leves (Mancester -> Manchester)", table_body_style),
        Paragraph("Validación final de nombres previamente depurados", table_body_style)
    ],
    [
        Paragraph("Comparación de Subconjuntos", table_body_style),
        Paragraph("Token Set Ratio: Compara conjuntos de palabras desordenadas e intersecciones", table_body_style),
        Paragraph("Ignora diferencias de orden y sufijos ('United FC' vs 'FC United')", table_body_style),
        Paragraph("Mapeo automatizado de cuotas de APIs vs base de datos", table_body_style)
    ],
    [
        Paragraph("Codificación Fonética Multilingüe", table_body_style),
        Paragraph("Double Metaphone: Genera claves fonéticas basadas en pronunciación multilingüe", table_body_style),
        Paragraph("Resuelve transliteraciones complejas (ej. Al-Ahly -> Al Ahli)", table_body_style),
        Paragraph("Unificación de ligas asiáticas y africanas en base de datos", table_body_style)
    ]
]

col_widths_4 = [100, 150, 140, 140]
t4 = Table(table_data_4, colWidths=col_widths_4)
t4.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), primary_color),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
]))
story.append(t4)
story.append(PageBreak())

# --- SECCIÓN 6 ---
story.append(Paragraph("6. Arquitectura Tecnológica en Tiempo Real: React, WebSockets y Redis 8", h1_style))
p6 = (
    "Para soportar consultas masivas de datasets históricos en paralelo con flujos en vivo de cuotas y liquidación de apuestas, "
    "se propone la siguiente pila e infraestructura tecnológica de alto rendimiento:<br/><br/>"
    "<b>APIs de Datos Incorporadas:</b><br/>"
    "• <i>OpticOdds:</i> Cuotas y props con latencias sub-800ms.<br/>"
    "• <i>TheRundown:</i> Movimientos de línea ultra rápidos (latencia < 200ms).<br/>"
    "• <i>API-Football:</i> Estadísticas de juego en vivo de 1,230+ competiciones mundiales.<br/><br/>"
    "<b>Capa de Datos Integrada en Redis 8:</b><br/>"
    "Redis 8 se utiliza como base de datos en memoria centralizada, reduciendo un 40% el uso de memoria comparado con pilas de múltiples bases de datos. Se implementa en 5 estructuras:<br/>"
    "1. <b>Redis Streams:</b> Cola de persistencia para la ingesta en alta frecuencia de cuotas.<br/>"
    "2. <b>Redis Sorted Sets (ZADD):</b> Ranking y priorización en tiempo real de surebets de mayor retorno.<br/>"
    "3. <b>Redis PubSub:</b> Distribución instantánea de alertas hacia los servidores de WebSockets.<br/>"
    "4. <b>Redis Key-Value Cache:</b> Almacenamiento de datos estáticos, perfiles e históricos de equipos.<br/>"
    "5. <b>Redis Bitmaps:</b> Analítica ultraligera en tiempo real de actividad de usuarios concurrentes.<br/><br/>"
    "<b>Canal de Sockets en React y Optimización de Rendimiento:</b><br/>"
    "• <i>Throttling y Batching:</i> Se evita actualizar el estado de React con cada tick del socket. Los datos se retienen en un <code>useRef</code> y un despachador actualiza la UI agrupada mediante <code>requestAnimationFrame</code> a un máximo estable de 60 FPS.<br/>"
    "• <i>Virtualización de Filas:</i> Utiliza renderizado de listas virtuales para mantener en el DOM únicamente las tarjetas de partidos actualmente visibles."
)
story.append(Paragraph(p6, body_style))
story.append(Spacer(1, 5))

code_text = """Ejemplo de Payload de Sockets para el Monitoreo de Apuestas:
{
  "event_type": "bet_settlement_update",
  "timestamp": "2026-03-30T21:45:12.890Z",
  "data": {
    "bet_id": "tx_987654321_arb",
    "market_type": "1X2_soccer_match",
    "match_id": "api_fb_837192",
    "home_team": "MC Alger",
    "away_team": "CR Belouizdad",
    "selected_outcome": "Home Win",
    "odds_placed": 2.80,
    "stake_amount": 365.00,
    "settlement_status": "WON",
    "gross_return": 1022.00,
    "net_profit": 657.00
  }
}"""
story.append(Preformatted(code_text, code_style))
story.append(PageBreak())

# --- SECCIÓN 7 ---
story.append(Paragraph("7. Recomendaciones y Conclusiones Operacionales", h1_style))
p7 = (
    "<b>A. Foco Estratégico en Ligas Menores:</b> Se recomienda orientar el motor de predicción a ligas de "
    "África, Asia y zonas de altitud de América Latina, ya que exhiben una ventaja de localía extrema no modelada de forma correcta por operadores globales.<br/><br/>"
    "<b>B. Integración y Automatización con Google Antigravity:</b><br/>"
    "Para codificar la plataforma, traslade este documento técnico a <b>Google Antigravity 2.0</b>. Al proveer este reporte "
    "completo al Agente de Antigravity en su <i>Manager View</i>, el sistema generará de forma asíncrona la lista de tareas y planes de implementación "
    "estructurados para React y Python, utilizando su navegador integrado para depurar las animaciones y el flujo de WebSockets en tiempo real.<br/><br/>"
    "<b>C. Redondeo de Surebets Obligatorio:</b> Se debe implementar por defecto un módulo de redondeo a enteros en los stakes de apuestas "
    "de arbitraje para evitar limitaciones rápidas de las cuentas de usuario por parte de los operadores blandos.<br/><br/>"
    "<b>D. Arquitectura de UI Defensiva:</b> El buffering con <code>requestAnimationFrame</code> y la virtualización garantizan "
    "una interfaz a 60 FPS sin interrupciones incluso bajo alta frecuencia de datos en vivo."
)
story.append(Paragraph(p7, body_style))

# Compilar documento
doc.build(story)
print("PDF built successfully.")