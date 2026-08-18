"""
bilan_pdf.py — Génère le Bilan Klemo en PDF (4 pages), script autonome.

Aucune dépendance à Streamlit. Utilisable en ligne de commande OU dans un notebook.

Dépendances :  pip install matplotlib jinja2
  + UN moteur de rendu au choix :
      - WeasyPrint : pip install weasyprint   (sur macOS : brew install pango gdk-pixbuf libffi)
      - OU Chromium : pip install playwright && python -m playwright install chromium
    Aucune lib système requise pour Chromium -> recommandé sur macOS.

------------------------------------------------------------------------------
UTILISATION EN NOTEBOOK
------------------------------------------------------------------------------
    import json
    from bilan_pdf import generate_pdf

    base_info = json.load(open("t5.json", encoding="utf-8"))

    # Mode démo (aucune API) — pour valider la maquette :
    generate_pdf(base_info, synth=None, out="BilanE7A3_Klemo.pdf")

    # Avec la vraie synthèse API (json_synth) :
    synth = json.load(open("json_synth.json", encoding="utf-8"))
    generate_pdf(base_info, synth=synth, out="bilan.pdf")

------------------------------------------------------------------------------
UTILISATION EN LIGNE DE COMMANDE
------------------------------------------------------------------------------
    python bilan_pdf.py --base t5.json --out BilanE7A3_Klemo.pdf
    python bilan_pdf.py --base t5.json --synth json_synth.json --out bilan.pdf
"""
from __future__ import annotations

import base64
import io
import json
import math
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from jinja2 import Template
# NB : ni weasyprint ni playwright ne sont importés ici — import paresseux dans
# _html_to_pdf(), pour que `import bilan_pdf` fonctionne même si l'un des deux manque.


# =============================================================================
#  1. EXTRACTION DES DONNÉES
# =============================================================================

def extract_info(base_info: dict) -> dict:
    """Partie 'Information' — extraite de t5.json (schéma connu)."""
    client = base_info["Client"]["PatClientDetail"][0]
    cash = base_info["Cashflow"]["PatCashflowDetail"][0]

    naissance = client.get("dateNaissance")
    age = datetime.today().year - int(str(naissance)[:4]) if naissance else None

    return {
        "id_user": client.get("id"),
        "statut_pro": client.get("statutPro") or "—",
        "age": age,
        "situation": _normaliser_situation(client.get("typeUnion")),
        "depenses_mensuelles": _num(cash.get("depensesCourantes")),
        "loyer_mensuel": _num(cash.get("loyerHabitationPrincipale")),
        "salaire_brut_annuel": _num(cash.get("revenusActivite")),
        "nb_parts_fiscales": _num(cash.get("nbPartFiscal")) or 1,
    }


def extract_synth(json_synth: dict) -> dict:
    """
    Mappe la vraie sortie de l'API Klemo vers le contrat du PDF.
    Schéma dérivé de func.display_bilan_synth. Accepte soit l'objet complet
    (avec la clé 'output'), soit directement le contenu de 'output'.
    """
    out = json_synth.get("output", json_synth)
    pat = out["patSynth"]

    asset = out["assetSynth"]
    cfr = out["cashflowCourantReel"]
    cfs = out["cashflowSynth"]
    imp = out["cashflowImpotsPhoto"]

    return {
        "patrimoine": {
            "total_brut": pat["patBrut"],
            "valeur_nette": pat["patNet"],
            "repartition": [
                {"label": "Financier", "value": pat["patFin"]},
                {"label": "Immobilier", "value": pat["patImmo"]},
                {"label": "Professionnel", "value": pat["patPro"]},
                {"label": "Emprunts", "value": pat["patEmprunt"]},
            ],
        },
        "projection": {
            "years": _parse_dates(_col(asset, "dates")),
            "favorable": _col(asset, "TotalPct95"),
            "median": _col(asset, "TotalPct50"),
            "defavorable": _col(asset, "TotalPct5"),
        },
        "revenus_charges": {
            "years": _parse_dates(_col(cfr, "dates")),
            "revenus": _col(cfr, "RevenusActiviteReel"),
            "charges": _col(cfr, "DepensesActiviteReel"),
        },
        "impots_bareme": {
            "impot_revenu": imp["IRBareme"],
            "prelevements_sociaux": imp["PSBareme"],
            "revenu_brut_total": imp["RevenuBrutTotal"],
            "taux_marginal": imp["TMI"] * 100,
            "taux_effectif": imp["TauxBaremeProgressif"] * 100,
            "taxes": imp["Taxes"],
            "tva": imp["TVARevenus"],
            "nb_parts": imp.get("NombrePartFiscale"),
        },
        "impots_invest": {
            "pfu_ir": imp["IRPreleve"],
            "pfu_ps": imp["PSPreleve"],
            "ifi": imp["MontantImpotsIFI"],
        },
        "impots_evolution": {
            "years": _parse_dates(_col(cfs, "dates")),
            # comme dans l'app : les colonnes numériques sont multipliées par -1
            "bareme": [-1 * (v or 0) for v in _col(cfs, "ImpotsBareme")],
            "invest": [-1 * (v or 0) for v in _col(cfs, "ImpotsInvest")],
            "autres": [-1 * (v or 0) for v in _col(cfs, "ImpotsAutres")],
        },
    }


def demo_synth(info: dict) -> dict:
    """Séries synthétiques cohérentes avec l'info — pour tester sans API."""
    annee = datetime.today().year
    horizon = 70
    years = [annee + i for i in range(horizon)]

    salaire = info["salaire_brut_annuel"] or 0
    charges_an = (info["depenses_mensuelles"] + info["loyer_mensuel"]) * 12
    net_epargne = max(salaire - charges_an, -charges_an)

    def projette(taux):
        val, serie = 0.0, []
        for _ in years:
            val = val * (1 + taux) + net_epargne
            serie.append(round(val))
        return serie

    favorable, median, defavorable = projette(0.06), projette(0.035), projette(0.01)
    revenus = [round(salaire) for _ in range(horizon)]
    charges = [round(charges_an * (0.999 ** i)) for i in range(horizon)]

    revenu_imposable = salaire * 0.9
    ir = _bareme_ir(revenu_imposable, info["nb_parts_fiscales"])
    taux_eff = (ir / revenu_imposable * 100) if revenu_imposable else 0.0

    return {
        "patrimoine": {
            "total_brut": median[9] if len(median) > 9 else 0,
            "valeur_nette": median[9] if len(median) > 9 else 0,
            "repartition": [
                {"label": "Liquidités", "value": 55},
                {"label": "Financier", "value": 30},
                {"label": "Immobilier", "value": 15},
            ],
        },
        "projection": {"years": years, "favorable": favorable,
                       "median": median, "defavorable": defavorable},
        "revenus_charges": {"years": years, "revenus": revenus, "charges": charges},
        "impots_bareme": {
            "impot_revenu": round(ir), "prelevements_sociaux": 0,
            "revenu_brut_total": round(revenu_imposable),
            "taux_marginal": _tmi(revenu_imposable, info["nb_parts_fiscales"]),
            "taux_effectif": round(taux_eff, 2), "taxes": 0, "tva": 0,
            "nb_parts": info["nb_parts_fiscales"],
        },
        "impots_invest": {"pfu_ir": 0, "pfu_ps": 0, "ifi": 0},
        "impots_evolution": {"years": years, "bareme": [ir] * horizon,
                             "invest": [0] * horizon, "autres": [0] * horizon},
    }


def build_report(base_info: dict, synth: dict | None) -> dict:
    """Assemble info + synthèse (synth=None -> mode démo)."""
    info = extract_info(base_info)
    data = demo_synth(info) if synth is None else extract_synth(synth)
    data["_mode"] = "demo" if synth is None else "live"
    data["info"] = info
    data["_generated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    return data


# =============================================================================
#  2. GRAPHIQUES (matplotlib -> PNG base64)
# =============================================================================

GREEN, GREEN_L, GOLD = "#178a63", "#4caf88", "#f4c220"
BLUE, BLUE_L, RED = "#2f6fdb", "#8fc0f2", "#e2493b"
INK, MUTED, GRID = "#1f2a37", "#8a94a3", "#e7ebf0"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.edgecolor": GRID, "axes.linewidth": 1, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 1,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.labelcolor": MUTED, "figure.dpi": 130,
})


def _eur_axis(x, _=None):
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x/1_000_000:.0f}M"
    if ax >= 1_000:
        return f"{x/1_000:.0f}k"
    return f"{x:.0f}"


def _clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)


def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()


def _pie_patrimoine(repartition):
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    labels = [r["label"] for r in repartition]
    colors = ["#4E79A7", "#F28E2B", "#E15759", "#59A14F", "#8a94a3"][: len(labels)]

    def _clean_num(v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.0
        return 0.0 if math.isnan(v) else abs(v)

    sizes = [_clean_num(r["value"]) for r in repartition]

    if sum(sizes) <= 0:
        # patrimoine nul : anneau gris neutre + mention "Aucune donnée"
        ax.pie([1], colors=["#e7ebf0"], startangle=90,
               wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
        ax.text(0, 0, "Aucune donnée", ha="center", va="center",
                fontsize=10, color=MUTED)
        from matplotlib.patches import Patch
        ax.legend([Patch(color=c) for c in colors], labels, loc="center left",
                  bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=10)
    else:
        wedges, *_ = ax.pie(sizes, colors=colors, startangle=90, counterclock=False,
                            wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
                  frameon=False, fontsize=10)
    ax.set_aspect("equal")
    return _b64(fig)


def _line_projection(years, fav, med, defav):
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    # couleurs alignées sur display_bilan_synth
    ax.plot(years, defav, color="#2E8B57", lw=2, ls=(0, (2, 2)), label="Scénario défavorable")
    ax.plot(years, med, color="#87CEEB", lw=2.5, label="Scénario médian")
    ax.plot(years, fav, color="#FFD700", lw=2, ls=(0, (2, 2)), label="Scénario favorable")
    ax.yaxis.set_major_formatter(FuncFormatter(_eur_axis))
    ax.set_ylabel("Montant (€)"); ax.set_xlabel("Date")
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="Scénario", title_fontsize=9)
    _clean(ax)
    return _b64(fig)


def _line_revenus_charges(years, revenus, charges):
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.plot(years, charges, color="#FFD700", lw=3, label="Charges")
    ax.plot(years, revenus, color="#2E8B57", lw=3, label="Revenus")
    ax.yaxis.set_major_formatter(FuncFormatter(_eur_axis))
    ax.set_ylabel("Montant (€)"); ax.set_xlabel("Date"); ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="Scénarios", title_fontsize=9)
    _clean(ax)
    return _b64(fig)


def _line_impots(years, bareme, invest, autres):
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.plot(years, bareme, color="#636EFA", lw=2.5, label="ImpotsBareme")
    ax.plot(years, invest, color="#EF553B", lw=2.5, label="ImpotsInvest")
    ax.plot(years, autres, color="#00CC96", lw=2.5, label="ImpotsAutres")
    ax.yaxis.set_major_formatter(FuncFormatter(_eur_axis))
    ax.set_ylabel("Montant (€)"); ax.set_xlabel("Date")
    if max(bareme + invest + autres, default=0) == 0:
        ax.set_ylim(-1, 1)
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="Scénarios", title_fontsize=9)
    _clean(ax)
    return _b64(fig)


# =============================================================================
#  3. TEMPLATE HTML + RENDU PDF
# =============================================================================

def _eur(x):
    try:
        return f"{float(x):,.0f} €".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


_HTML = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 22mm 16mm; }
  * { box-sizing:border-box; }
  body { font-family:'DejaVu Sans',Arial,sans-serif; color:#1f2a37; font-size:12px; line-height:1.5; margin:0; }
  h2 { font-size:17px; margin:22px 0 6px; } h3 { font-size:14px; margin:14px 0 4px; }
  .muted { color:#6b7280; } .small { font-size:11px; }
  .section { page-break-inside:avoid; }
  .page-break { page-break-before:always; height:0; margin:0; padding:0; border:0; }
  .head-icon { color:#178a63; font-weight:700; }
  .hr { border:0; border-top:1px solid #e6eaef; margin:10px 0; }
  .info-line { margin:2px 0; }
  .fields { display:flex; flex-wrap:wrap; gap:10px 18px; margin-top:8px; }
  .field { flex:1 1 150px; }
  .field .lbl { color:#6b7280; font-size:11px; }
  .field .val { background:#f3f5f7; border:1px solid #e6eaef; border-radius:8px; padding:8px 12px; margin-top:3px; font-size:13px; }
  .card { background:#f3f5f7; border-radius:12px; padding:16px 18px; margin:10px 0; }
  .card .title { font-size:15px; font-weight:700; }
  .card .sub { color:#6b7280; font-size:11px; margin-bottom:8px; }
  .kpi-row { display:flex; gap:18px; } .kpi { flex:1; }
  .kpi .big { font-size:22px; font-weight:700; } .kpi .cap { color:#6b7280; font-size:11px; }
  .band { background:#e7f4ec; border-radius:8px; padding:9px 14px; margin-top:10px; font-size:13px; }
  ul.detail { margin:6px 0; padding-left:16px; } ul.detail li { margin:2px 0; }
  .chart { text-align:center; margin:8px 0; } .chart img { max-width:100%; }
  .center { text-align:center; }
  .total { text-align:center; margin-top:6px; }
  .total .cap { color:#6b7280; font-size:12px; } .total .big { font-size:16px; font-weight:700; }
  .footer { color:#6b7280; font-size:9px; text-align:center; margin-top:6px; }
  .demo-tag { display:inline-block; background:#fff4d6; color:#8a6d00; border-radius:6px; padding:1px 7px; font-size:9px; margin-left:6px; }
</style></head><body>

<div class="section">
  <div class="head-icon">👤 Information{% if d._mode=='demo' %}<span class="demo-tag">DONNÉES DÉMO</span>{% endif %}</div>
  <hr class="hr">
  <div class="info-line"><span class="muted">ID User :</span> {{ i.id_user }}</div>
  <div class="info-line"><span class="muted">Statut Pro :</span> {{ i.statut_pro }}</div>
  <div class="fields">
    <div class="field"><div class="lbl">Mon Âge</div><div class="val">{{ i.age }}</div></div>
    <div class="field"><div class="lbl">Dépenses courantes/mo (€)</div><div class="val">{{ '%.0f'|format(i.depenses_mensuelles) }}</div></div>
    <div class="field"><div class="lbl">Salaire brut annuel (€)</div><div class="val">{{ '%.0f'|format(i.salaire_brut_annuel) }}</div></div>
    <div class="field"><div class="lbl">Situation personnelle</div><div class="val">{{ i.situation }}</div></div>
    <div class="field"><div class="lbl">Loyer mensuel (€)</div><div class="val">{{ '%.0f'|format(i.loyer_mensuel) }}</div></div>
  </div>
</div>

<div class="section">
  <h3>Projection de votre patrimoine brut</h3>
  <div class="muted small">Répartition par catégorie</div>
  <div class="chart"><img src="{{ img_pie }}"></div>
  <div class="total"><div class="cap">Total brut</div><div class="big">{{ eur(p.total_brut) }}</div></div>
  <div class="band">Valeur nette des biens : <b>{{ eur(p.valeur_nette) }}</b></div>
</div>

<div class="page-break"></div>
<div class="section">
  <div class="muted">Estimation future de la valeur de vos investissements :</div>
  <h3 class="center">Vos 3 scénarios d'évolution de votre patrimoine dans les années à venir</h3>
  <div class="chart"><img src="{{ img_proj }}"></div>
</div>
<div class="section">
  <h2>Évolution de vos revenus et charges</h2>
  <h3 class="center">Revenus et charges ajustés de l'inflation au fil des années</h3>
  <div class="chart"><img src="{{ img_rc }}"></div>
</div>

<div class="page-break"></div>
<div class="section">
  <h2>🧾 Vos impôts</h2>
  <div class="muted">En fonction des données renseignées, nous avons estimé vos impôts :</div>
  <div class="card">
    <div class="title">Impôts au barème pour l'année en cours</div>
    <div class="sub">Ceux de votre déclaration annuelle</div>
    <div class="kpi-row">
      <div class="kpi"><div class="big">{{ eur(ib.impot_revenu) }}</div><div class="cap">Impôt sur le revenu</div></div>
      <div class="kpi"><div class="big">{{ eur(ib.prelevements_sociaux) }}</div><div class="cap">Prélèvements sociaux</div></div>
    </div>
  </div>
  <h3>📄 Détail du calcul</h3>
  <div class="card">
    <b>Nombre de parts fiscales : {{ '%.0f'|format(ib.nb_parts if ib.nb_parts is not none else i.nb_parts_fiscales) }}</b>
    <hr class="hr"><div><b>Impôts au barème progressif</b></div>
    <ul class="detail">
      <li><b>Revenu brut total :</b> {{ eur(ib.revenu_brut_total) }}</li>
      <li><b>Taux marginal d'imposition :</b> {{ '%.0f'|format(ib.taux_marginal) }} %</li>
      <li><b>Taux effectif d'imposition :</b> {{ '%.2f'|format(ib.taux_effectif) }} %</li>
      <li><b>Impôt sur le revenu au barème :</b> {{ eur(ib.impot_revenu) }}</li>
      <li><b>Prélèvements sociaux au barème :</b> {{ eur(ib.prelevements_sociaux) }}</li>
    </ul>
  </div>
  <div class="card"><div><b>Autres impôts</b></div>
    <ul class="detail">
      <li><b>Taxes :</b> {{ eur(ib.taxes) }}</li>
      <li><b>TVA sur revenus :</b> {{ eur(ib.tva) }}</li>
    </ul>
  </div>
</div>

<div class="page-break"></div>
<div class="section">
  <div class="card">
    <div class="title">Impôts prélevés sur les investissements</div>
    <div class="sub">Prélèvement forfaitaire (ex : PFU…)</div>
    <div class="kpi-row">
      <div class="kpi"><div class="big">{{ eur(iv.pfu_ir) }}</div><div class="cap">Impôt sur le revenu</div></div>
      <div class="kpi"><div class="big">{{ eur(iv.pfu_ps) }}</div><div class="cap">Prélèvements sociaux</div></div>
    </div>
  </div>
  <div class="card">
    <div class="title">Impôts sur la fortune immobilière</div>
    <div class="sub">Si assujetti</div>
    <div class="kpi"><div class="big">{{ eur(iv.ifi) }}</div></div>
  </div>
  <h2>Évolution de vos impôts</h2>
  <div class="chart"><img src="{{ img_imp }}"></div>
</div>

<div class="footer">Bilan Klemo — généré le {{ d._generated_at }}{% if d._mode=='demo' %} — données de démonstration{% endif %}</div>
</body></html>
""")


def render_html(d: dict) -> str:
    p, proj = d["patrimoine"], d["projection"]
    rc, imp = d["revenus_charges"], d["impots_evolution"]
    return _HTML.render(
        d=d, i=d["info"], p=p, ib=d["impots_bareme"], iv=d["impots_invest"], eur=_eur,
        img_pie=_pie_patrimoine(p["repartition"]),
        img_proj=_line_projection(proj["years"], proj["favorable"], proj["median"], proj["defavorable"]),
        img_rc=_line_revenus_charges(rc["years"], rc["revenus"], rc["charges"]),
        img_imp=_line_impots(imp["years"], imp["bareme"], imp["invest"], imp["autres"]),
    )


def _weasyprint_ok() -> bool:
    """True si WeasyPrint et ses libs natives sont chargeables."""
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


def _html_to_pdf(html: str, backend: str = "auto") -> bytes:
    """
    Convertit le HTML en PDF.
      backend = "auto"       -> WeasyPrint si dispo, sinon Chromium (Playwright)
      backend = "weasyprint" -> WeasyPrint (nécessite pango/gobject ; cf. macOS)
      backend = "chromium"   -> Playwright/Chromium (aucune lib système requise)
    """
    if backend == "auto":
        backend = "weasyprint" if _weasyprint_ok() else "chromium"

    if backend == "weasyprint":
        from weasyprint import HTML
        return HTML(string=html).write_pdf()

    if backend == "chromium":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise RuntimeError(
                "Backend 'chromium' indisponible. Installe-le une fois :\n"
                "    pip install playwright\n"
                "    python -m playwright install chromium"
            ) from e

        def _render() -> bytes:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.set_content(html, wait_until="load")
                pdf = page.pdf(print_background=True, prefer_css_page_size=True)
                browser.close()
            return pdf

        # Jupyter fait tourner une boucle asyncio : l'API sync de Playwright
        # refuse de s'exécuter dedans. On l'exécute alors dans un thread dédié
        # (qui n'a pas de boucle en cours) et on attend le résultat.
        import asyncio
        try:
            asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False

        if in_loop:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(_render).result()
        return _render()

    raise ValueError(f"backend inconnu : {backend!r} (auto | weasyprint | chromium)")


def generate_pdf(base_info: dict, synth: dict | None = None,
                 out: str | None = None, backend: str = "auto") -> bytes:
    """
    Génère le bilan.
      base_info : dict issu de t5.json
      synth     : dict json_synth (sortie API) ou None pour le mode démo
      out       : si fourni, écrit le PDF sur disque à ce chemin
      backend   : "auto" (défaut) | "weasyprint" | "chromium"
    Renvoie les bytes du PDF.
    """
    d = build_report(base_info, synth)
    pdf = _html_to_pdf(render_html(d), backend=backend)
    if out:
        Path(out).write_bytes(pdf)
        print(f"✅ PDF généré : {out}  ({len(pdf)//1024} Ko)"
              + ("  [mode démo]" if synth is None else ""))
    return pdf


async def generate_pdf_async(base_info: dict, synth: dict | None = None,
                             out: str | None = None) -> bytes:
    """
    Variante ASYNC (backend Chromium) — à utiliser en Jupyter avec `await` :

        pdf = await generate_pdf_async(base_info, synth=None, out="bilan.pdf")

    Insensible aux problèmes de boucle asyncio du notebook.
    """
    from playwright.async_api import async_playwright
    d = build_report(base_info, synth)
    html = render_html(d)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        pdf = await page.pdf(print_background=True, prefer_css_page_size=True)
        await browser.close()
    if out:
        Path(out).write_bytes(pdf)
        print(f"✅ PDF généré : {out}  ({len(pdf)//1024} Ko)"
              + ("  [mode démo]" if synth is None else ""))
    return pdf


# =============================================================================
#  Helpers métier
# =============================================================================

def _normaliser_situation(valeur):
    """Règle métier : toute variante 'marié...' -> 'marié(e)'."""
    if valeur is None:
        return "—"
    return "marié(e)" if "marié" in str(valeur).lower() else valeur


def _num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _col(records, key):
    """Extrait une colonne d'une liste de dicts (records type DataFrame)."""
    return [r.get(key) for r in records]


def _parse_dates(values):
    """Convertit une liste de dates (str/num) en objets datetime pour l'axe X."""
    from datetime import datetime as _dt
    out = []
    for v in values:
        if isinstance(v, (int, float)):
            out.append(_dt(int(v), 1, 1)); continue
        s = str(v)
        parsed = None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%Y-%m", "%Y"):
            try:
                parsed = _dt.strptime(s[:len(fmt) + 2] if "T" in s else s[:len(fmt)], fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = _dt.fromisoformat(s)
            except ValueError:
                parsed = _dt(int(s[:4]), 1, 1)
        out.append(parsed)
    return out


_TRANCHES = [
    (0, 11294, 0.0), (11294, 28797, 0.11), (28797, 82341, 0.30),
    (82341, 177106, 0.41), (177106, math.inf, 0.45),
]  # barème indicatif — à remplacer par les valeurs de json_synth en mode live


def _bareme_ir(revenu_imposable, nb_parts):
    nb_parts = max(nb_parts, 1)
    part = revenu_imposable / nb_parts
    impot = sum((min(part, h) - b) * t for b, h, t in _TRANCHES if part > b)
    return max(impot * nb_parts, 0.0)


def _tmi(revenu_imposable, nb_parts):
    nb_parts = max(nb_parts, 1)
    part = revenu_imposable / nb_parts
    tmi = 0.0
    for b, _, t in _TRANCHES:
        if part > b:
            tmi = t * 100
    return tmi


# =============================================================================
#  CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Génère le Bilan Klemo en PDF.")
    ap.add_argument("--base", required=True, help="Chemin du t5.json")
    ap.add_argument("--synth", help="Chemin du json_synth (sortie API). Absent = mode démo.")
    ap.add_argument("--out", default="BilanKlemo.pdf", help="PDF de sortie")
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "weasyprint", "chromium"],
                    help="Moteur de rendu (auto = WeasyPrint sinon Chromium)")
    args = ap.parse_args()

    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    synth = json.loads(Path(args.synth).read_text(encoding="utf-8")) if args.synth else None
    generate_pdf(base, synth, out=args.out, backend=args.backend)