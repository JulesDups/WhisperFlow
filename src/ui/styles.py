"""
WhisperFlow UI — QSS stylesheet (Hegoatek Design System, light mode).

Tous les tokens viennent de `theme.py`. Aucun hex codé en dur ici : si tu
dois changer une couleur, modifie la palette dans theme.py.

Architecture QSS :
- Sélecteurs par `objectName` (`#centralFrame`, `#sectionHeader`, …) pour
  cibler précisément les widgets instanciés par `widgets/`.
- Sélecteurs par `property` dynamique (`[state="recording"]`) pour les états
  qui changent à l'exécution.
- QSS ne supporte pas `box-shadow`, `@keyframes`, `backdrop-filter` : ombres
  via `QGraphicsDropShadowEffect`, pulses via `QPropertyAnimation`.

Typographie : DM Sans (display) + DM Mono (metadata/labels). Poids bumpés
sur toutes les zones de lecture pour garantir la lisibilité.
"""

from __future__ import annotations

from . import theme


def get_main_stylesheet() -> str:
    """QSS global de l'application, assemblée à partir des tokens theme."""
    display = theme.display_family()
    mono = theme.mono_family()

    return f"""
    /* ============================================================
       WhisperFlow — Hegoatek light mode
       ============================================================ */

    /* Defaults */
    QWidget {{
        background-color: transparent;
        color: {theme.TEXT};
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 14px;
        font-weight: 500;
    }}

    QMainWindow {{
        background-color: transparent;
    }}

    /* Central frame (hosts the rounded card + drop shadow) */
    #centralFrame {{
        background-color: {theme.BG};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_XL}px;
    }}

    /* Title bar */
    #titleBar {{
        background-color: transparent;
        border-top-left-radius: {theme.RADIUS_XL}px;
        border-top-right-radius: {theme.RADIUS_XL}px;
    }}

    #brandEyebrow {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 2px;
        color: {theme.GOLD};
    }}

    #brandName {{
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 20px;
        font-weight: 800;
        color: {theme.TEXT};
        letter-spacing: -0.3px;
    }}

    #brandVersion {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 400;
        color: {theme.TEXT_MUTED};
    }}

    /* Content area */
    #contentArea {{
        background-color: transparent;
    }}

    /* ============================================================
       Section headers (eyebrow labels)
       ============================================================ */

    #sectionHeader, #eyebrow {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 2px;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    /* ============================================================
       Status bar
       ============================================================ */

    #statusBar {{
        background-color: transparent;
    }}

    #statusBarLabel {{
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 15px;
        font-weight: 700;
        color: {theme.TEXT};
        background-color: transparent;
    }}

    #statusBarLabel[state="error"] {{
        color: {theme.DANGER};
    }}

    #statusBarLabel[state="recording"] {{
        color: {theme.RUST};
    }}

    /* ============================================================
       Level meter
       ============================================================ */

    #levelMeter {{
        background-color: transparent;
    }}

    #levelMeterDb {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 11px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    /* ============================================================
       Metric cards (GPU, MODEL, SESSION)
       ============================================================ */

    #metricCard {{
        background-color: {theme.BG_ELEVATED};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_MD}px;
    }}

    #metricValue {{
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 19px;
        font-weight: 800;
        color: {theme.TEXT};
        background-color: transparent;
        letter-spacing: -0.2px;
    }}

    #metricHint {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    /* GpuGauge specific */
    #gpuGauge {{
        background-color: transparent;
    }}

    /* ============================================================
       Source toggle (MIC / URL segmented pill)
       ============================================================ */

    #sourceToggle {{
        background-color: transparent;
    }}

    QPushButton#sourceToggleBtn {{
        background-color: {theme.BG_ELEVATED};
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER};
        padding: 10px 16px;
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    QPushButton#sourceToggleBtn[segment="left"] {{
        border-top-left-radius: {theme.RADIUS_MD}px;
        border-bottom-left-radius: {theme.RADIUS_MD}px;
        border-right: none;
    }}

    QPushButton#sourceToggleBtn[segment="right"] {{
        border-top-right-radius: {theme.RADIUS_MD}px;
        border-bottom-right-radius: {theme.RADIUS_MD}px;
    }}

    QPushButton#sourceToggleBtn:hover {{
        color: {theme.TEXT};
        background-color: {theme.BG_HOVER};
    }}

    QPushButton#sourceToggleBtn:checked {{
        background-color: {theme.INK};
        color: {theme.CREAM};
        border-color: {theme.INK};
    }}

    /* ============================================================
       URL panel
       ============================================================ */

    #urlPanel {{
        background-color: transparent;
    }}

    QLineEdit#urlInput {{
        background-color: {theme.BG_ELEVATED};
        color: {theme.TEXT};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_MD}px;
        padding: 10px 14px;
        font-family: "{mono}", "Consolas", monospace;
        font-size: 12px;
        font-weight: 500;
        selection-background-color: {theme.ACCENT_STRONG};
        selection-color: {theme.INK};
    }}

    QLineEdit#urlInput:focus {{
        border: 1px solid {theme.BORDER_GOLD};
        background-color: {theme.BG_ELEVATED};
    }}

    QLineEdit#urlInput::placeholder {{
        color: {theme.TEXT_MUTED};
    }}

    /* Primary action button (INK on CREAM → high-contrast dark button) */
    QPushButton#urlSubmitBtn {{
        background-color: {theme.INK};
        color: {theme.CREAM};
        border: none;
        border-radius: {theme.RADIUS_MD}px;
        padding: 10px 18px;
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 1px;
    }}

    QPushButton#urlSubmitBtn:hover {{
        background-color: {theme.GOLD};
        color: {theme.INK};
    }}

    QPushButton#urlSubmitBtn:disabled {{
        background-color: {theme.BG_HOVER};
        color: {theme.TEXT_MUTED};
    }}

    QPushButton#urlSubmitBtn[busy="true"] {{
        background-color: {theme.RUST};
        color: {theme.CREAM};
    }}

    QPushButton#urlSubmitBtn[busy="true"]:hover {{
        background-color: {theme.DANGER};
    }}

    #urlMeta {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 11px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
        padding: 2px 0;
    }}

    QProgressBar#urlProgress {{
        background-color: {theme.BG_HOVER};
        border: none;
        border-radius: 3px;
    }}

    QProgressBar#urlProgress::chunk {{
        background-color: {theme.GOLD};
        border-radius: 3px;
    }}

    #urlProgressLabel {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    /* ============================================================
       Transcript view (3-states: empty / result / error)
       ============================================================ */

    #transcriptView {{
        background-color: transparent;
    }}

    #transcriptBody {{
        background-color: {theme.BG_ELEVATED};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_LG}px;
    }}

    QTextEdit#transcriptText {{
        background-color: transparent;
        border: none;
        color: {theme.TEXT};
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 15px;
        font-weight: 500;
        padding: 0;
        selection-background-color: {theme.ACCENT_STRONG};
        selection-color: {theme.INK};
    }}

    QTextEdit#transcriptText QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}

    QTextEdit#transcriptText QScrollBar::handle:vertical {{
        background: {theme.BORDER_STRONG};
        border-radius: 4px;
        min-height: 24px;
    }}

    QTextEdit#transcriptText QScrollBar::handle:vertical:hover {{
        background: {theme.TEXT_DIM};
    }}

    QTextEdit#transcriptText QScrollBar::add-line:vertical,
    QTextEdit#transcriptText QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    #langBadge {{
        background-color: {theme.ACCENT_SOFT};
        color: {theme.INK};
        border: 1px solid {theme.BORDER_GOLD};
        border-radius: 10px;
        padding: 3px 12px;
        font-family: "{mono}", "Consolas", monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
    }}

    #emptyTitle {{
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 20px;
        font-weight: 700;
        color: {theme.TEXT};
        background-color: transparent;
        letter-spacing: -0.2px;
    }}

    #emptyHint {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 11px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    #errorTitle {{
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: {theme.DANGER};
        background-color: transparent;
    }}

    #errorDetail {{
        font-family: "{mono}", "Consolas", monospace;
        font-size: 11px;
        font-weight: 500;
        color: {theme.TEXT_DIM};
        background-color: transparent;
    }}

    QPushButton#retryBtn {{
        background-color: {theme.DANGER_BG};
        color: {theme.DANGER};
        border: 1px solid {theme.DANGER_BORDER};
        border-radius: {theme.RADIUS_MD}px;
        padding: 10px 22px;
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 700;
    }}

    QPushButton#retryBtn:hover {{
        background-color: {theme.DANGER};
        color: {theme.CREAM};
    }}

    /* ============================================================
       Menu button (≡)
       ============================================================ */

    QPushButton#menuButton {{
        background-color: {theme.BG_ELEVATED};
        color: {theme.TEXT_DIM};
        border: 1px solid {theme.BORDER};
        border-radius: {theme.RADIUS_SM}px;
        font-size: 18px;
        font-weight: 700;
        padding: 0;
    }}

    QPushButton#menuButton:hover {{
        color: {theme.INK};
        border-color: {theme.BORDER_GOLD};
        background-color: {theme.ACCENT_SOFT};
    }}

    QPushButton#menuButton:pressed {{
        background-color: {theme.ACCENT_STRONG};
    }}

    QMenu#appMenu {{
        background-color: {theme.BG_ELEVATED};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: {theme.RADIUS_MD}px;
        padding: 6px;
        color: {theme.TEXT};
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 600;
    }}

    QMenu#appMenu::item {{
        padding: 9px 20px;
        border-radius: {theme.RADIUS_SM}px;
        color: {theme.TEXT};
    }}

    QMenu#appMenu::item:selected {{
        background-color: {theme.INK};
        color: {theme.CREAM};
    }}

    QMenu#appMenu::separator {{
        height: 1px;
        background: {theme.BORDER};
        margin: 4px 2px;
    }}

    /* ============================================================
       Close button (×)
       ============================================================ */

    QPushButton#closeButton {{
        background-color: transparent;
        color: {theme.TEXT_MUTED};
        border: none;
        border-radius: {theme.RADIUS_SM}px;
        font-size: 20px;
        font-weight: 700;
        padding: 0;
    }}

    QPushButton#closeButton:hover {{
        background-color: {theme.DANGER_BG};
        color: {theme.DANGER};
    }}

    /* ============================================================
       Tooltip
       ============================================================ */

    QToolTip {{
        background-color: {theme.INK};
        color: {theme.CREAM};
        border: 1px solid {theme.INK};
        border-radius: {theme.RADIUS_SM}px;
        padding: 6px 12px;
        font-family: "{display}", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 500;
    }}
    """
