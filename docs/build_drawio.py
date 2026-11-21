"""Generate docs/pipeline.drawio. Colour = real status (green verified, yellow written, grey planned)."""

from xml.sax.saxutils import escape

GREEN = "fillColor=#d5e8d4;strokeColor=#82b366;"
YELLOW = "fillColor=#fff2cc;strokeColor=#d6b656;"
GREY = "fillColor=#f5f5f5;strokeColor=#999999;fontColor=#666666;dashed=1;"
BOX = "rounded=1;whiteSpace=wrap;html=1;fontSize=11;arcSize=8;"
LANE = "rounded=1;whiteSpace=wrap;html=1;fillColor=none;dashed=1;verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontStyle=1;fontSize=13;arcSize=1;"

lanes = [
    ("L1", "SOURCE — Mac (local)", 20, 60, 330, 860, "strokeColor=#666666;"),
    ("L2", "FLUX LENT — Snowflake · quotidien · données agrégées · finance & commercial", 380, 60, 1150, 420, "strokeColor=#29B5E8;fontColor=#1A7FA8;"),
    ("L3", "FLUX RAPIDE — Databricks · ~1 min · événements · pilotage opérationnel", 380, 500, 1150, 240, "strokeColor=#FF3621;fontColor=#C2280F;"),
    ("L4", "VALIDATION — même projet dbt, sans cloud", 380, 760, 1150, 160, "strokeColor=#666666;"),
    ("L5", "CONSOMMATION", 1560, 60, 320, 680, "strokeColor=#F2C811;fontColor=#8A6D00;"),
]

nodes = [
    ("S1", "<b>API Recherche d'entreprises (SIRENE)</b><br>profil agrégé : 7 210 établissements<br>secteur × taille × commune, sans nom", 50, 110, 270, 80, GREEN),
    ("S2", "<b>generate_erp.py</b> — ERP simulé, seed 42<br>1 200 clients · 39 k commandes · 91 k lignes<br>saisonnalité, Pareto, churn, ruptures<br>70 anomalies injectées → manifest", 50, 230, 270, 100, GREEN),
    ("S3", "<b>PostgreSQL 16 — rhone_erp</b><br>schéma erp · 12 tables<br>statuts + updated_at (incrémental)", 50, 370, 270, 80, GREEN),
    ("S4", "<b>extract_daily.py</b> (chaque nuit)<br>lignes agrégées jour × client × produit<br>+ deltas documents + snapshots référentiels<br>→ CSV gzip / batch", 50, 490, 270, 100, GREEN),
    ("S5", "<b>event_emitter.py</b><br>événements JSON commandes / expéditions<br>micro-batch ~1 min", 50, 640, 270, 80, GREY),

    ("F1", "<b>push_to_snowflake.py</b><br>PUT → stage @landing/&lt;batch&gt;", 410, 110, 200, 80, YELLOW),
    ("F2", "<b>BRONZE</b><br>COPY INTO idempotent<br>Task 06:00 Europe/Paris<br>append-only + source_file", 650, 110, 200, 90, YELLOW),
    ("F3", "<b>SILVER</b> (dbt)<br>typage · dernière version<br>quarantaine des anomalies", 890, 110, 200, 90, YELLOW),
    ("F4", "<b>GOLD</b> (dbt) — modèle en étoile<br>dim client / produit / agence / date<br>fct_ventes_jour (incrémental) · fct_factures<br>CA-marge · DSO · balance âgée · taux de service", 1130, 110, 260, 110, YELLOW),
    ("F5", "<b>Accès réglementés</b><br>10 rôles RBAC · row access par agence<br>masking PII (RGPD) + finance · tags", 1130, 280, 260, 90, YELLOW),
    ("F6", "<b>ml_churn_features</b> (dbt)<br>→ Snowpark ML (prévu)", 890, 280, 200, 70, YELLOW),

    ("D1", "<b>Volume Unity Catalog</b><br>landing/events", 410, 560, 200, 70, GREY),
    ("D2", "<b>BRONZE</b><br>Auto Loader · streaming table", 650, 560, 200, 70, GREY),
    ("D3", "<b>SILVER</b><br>dédup événements (at-least-once)", 890, 560, 200, 70, GREY),
    ("D4", "<b>GOLD ops live</b><br>carnet · ruptures en cours · CA du jour", 1130, 560, 260, 70, GREY),

    ("C1", "<b>DuckDB local</b> — même projet dbt<br>64 tests ✔ dont vérité terrain 70 / 70", 410, 810, 280, 70, GREEN),
    ("C2", "<b>GitHub Actions</b><br>Postgres service → extract → dbt build", 730, 810, 280, 70, YELLOW),
    ("C3", "<b>Site de doc dbt</b><br>graphe de lignage (GitHub Pages)", 1050, 810, 260, 70, YELLOW),

    ("P1", "<b>Power BI — DAF & commercial</b><br>Snowflake · RD_POWERBI_SVC ou SSO<br>sécurité appliquée par Snowflake", 1590, 120, 260, 90, GREY),
    ("P2", "<b>Power BI — Ops live</b><br>Databricks SQL Warehouse", 1590, 560, 260, 70, GREY),
    ("LEG", "<b>Légende</b><br><span style='background:#d5e8d4'>&nbsp;vert&nbsp;</span> construit et vérifié en local<br><span style='background:#fff2cc'>&nbsp;jaune&nbsp;</span> écrit, à valider sur la plateforme<br><span style='background:#f5f5f5'>&nbsp;gris&nbsp;</span> prévu", 1590, 780, 260, 110, "fillColor=#ffffff;strokeColor=#666666;align=left;spacingLeft=10;"),
]

# (source, target, label, extra style, waypoints) — waypoints keep lines out of the boxes
edges = [
    ("S1", "S2", "", "", []), ("S2", "S3", "COPY", "", []), ("S3", "S4", "SQL", "", []),
    ("S3", "S5", "CDC (prévu)", "exitX=0;exitY=0.5;entryX=0;entryY=0.5;", [(35, 410), (35, 680)]),
    ("S4", "F1", "nuit", "exitX=1;exitY=0.3;entryX=0;entryY=0.5;", [(368, 520), (368, 150)]),
    ("F1", "F2", "", "", []), ("F2", "F3", "", "", []), ("F3", "F4", "", "", []),
    ("F4", "P1", "Import / DirectQuery", "", []),
    ("F4", "F6", "", "exitX=0;exitY=0.85;entryX=1;entryY=0.5;", [(1110, 203), (1110, 315)]),
    ("S5", "D1", "~1 min", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", [(395, 680), (395, 595)]),
    ("D1", "D2", "", "", []), ("D2", "D3", "", "", []), ("D3", "D4", "", "", []),
    ("D4", "P2", "DirectQuery", "", []),
    ("S4", "C1", "mêmes fichiers", "exitX=1;exitY=0.8;entryX=0;entryY=0.5;", [(356, 570), (356, 845)]),
    ("C1", "C2", "", "", []), ("C2", "C3", "", "", []),
]

cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
cells.append('<mxCell id="T" value="&lt;b&gt;Rhône Distribution Lakehouse&lt;/b&gt; — pipeline de bout en bout (ERP simulé, enrichissements réels)" '
             'style="text;html=1;fontSize=18;align=left;" vertex="1" parent="1"><mxGeometry x="20" y="15" width="1200" height="30" as="geometry"/></mxCell>')
for cid, label, x, y, w, h, style in lanes:
    cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{LANE}{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
for cid, label, x, y, w, h, style in nodes:
    cells.append(f'<mxCell id="{cid}" value="{escape(label, {chr(34): "&quot;"})}" style="{BOX}{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
cells.append('<mxCell id="E_sec" style="endArrow=block;dashed=1;html=1;strokeColor=#b85450;" edge="1" parent="1" source="F5" target="F4" value="policies (post-hook dbt)">'
             '<mxGeometry relative="1" as="geometry"/></mxCell>')
for i, (s, t, label, extra, points) in enumerate(edges):
    pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
    geometry = f'<mxGeometry relative="1" as="geometry"><Array as="points">{pts}</Array></mxGeometry>' if points \
        else '<mxGeometry relative="1" as="geometry"/>'
    cells.append(f'<mxCell id="E{i}" value="{escape(label)}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;fontSize=10;labelBackgroundColor=#ffffff;{extra}" '
                 f'edge="1" parent="1" source="{s}" target="{t}">{geometry}</mxCell>')

xml = ('<mxfile host="app.diagrams.net"><diagram id="pipeline" name="Pipeline">'
       '<mxGraphModel dx="1900" dy="1000" grid="1" gridSize="10" page="1" pageWidth="1920" pageHeight="1000">'
       '<root>' + "".join(cells) + '</root></mxGraphModel></diagram></mxfile>')
open("docs/pipeline.drawio", "w", encoding="utf-8").write(xml)
print("docs/pipeline.drawio written")
