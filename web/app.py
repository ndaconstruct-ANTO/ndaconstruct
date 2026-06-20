"""Interface web locale (facultative) basée sur Streamlit.

Lancement :
    pip install streamlit
    python -m streamlit run web/app.py

Cette interface reste en mode SIMULATION : elle ne génère aucune image réelle et
n'engage aucune dépense. Elle sert à explorer les combinaisons, les prompts, les
métadonnées et les statistiques avant toute génération payante.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Rend le paquet `src` importable quand on lance via streamlit.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src.combination_generator import ConfigBundle  # noqa: E402
from src.main import PipelineOptions, run_pipeline  # noqa: E402
from src.quality_control import summarize  # noqa: E402


st.set_page_config(page_title="Lionceaux NFT — Simulation", layout="wide")
st.title("🦁 Générateur de collection NFT — Lionceaux")
st.caption("Mode simulation : aucune image réelle, aucune dépense.")

bundle = ConfigBundle.load("config/collection.yaml")

with st.sidebar:
    st.header("Paramètres")
    count = st.number_input("Nombre d'images", min_value=1, max_value=5000, value=10, step=1)
    seed = st.number_input(
        "Seed maître", min_value=0, value=int(bundle.collection["generation"]["master_seed"])
    )
    resolution = st.selectbox("Résolution", [512, 1024, 2048, 4096], index=2)

    fur_keys = [f["key"] for f in bundle.fur_colors]
    fur_names = {f["key"]: f["name"] for f in bundle.fur_colors}
    sel_fur = st.multiselect(
        "Pelages autorisés (vide = tous)", fur_keys, format_func=lambda k: fur_names[k]
    )

    style_keys = [s["key"] for s in bundle.styles]
    style_names = {s["key"]: s["name"] for s in bundle.styles}
    sel_styles = st.multiselect(
        "Styles autorisés (vide = tous)", style_keys, format_func=lambda k: style_names[k]
    )

    write = st.checkbox("Écrire les fichiers de sortie", value=False)
    run = st.button("Générer (simulation)", type="primary")

if run:
    options = PipelineOptions(
        count=int(count),
        provider="simulation",
        test_mode=True,
        seed=int(seed),
        width=int(resolution),
        height=int(resolution),
        write_outputs=write,
        allowed_traits={"fur_colors": sel_fur, "styles": sel_styles},
    )
    result = run_pipeline(options)

    st.success(f"{len(result.characters)} personnages générés (simulation).")
    st.write("**Contrôle qualité :**", summarize(result.qc))

    rows = [
        {
            "ID": c.id,
            "Pelage": c.fur["name"],
            "Yeux": c.eyes["name"],
            "Style": c.style["name"],
            "Objet": c.obj["name"],
            "Rareté": (c.rarity or {}).get("name", ""),
            "Seed": c.seed,
        }
        for c in result.characters
    ]
    st.subheader("Combinaisons")
    st.dataframe(rows, use_container_width=True)

    st.subheader("Statistiques de rareté")
    for trait, dist in result.stats["traits"].items():
        with st.expander(trait):
            st.dataframe(
                [{"Valeur": k, "Compte": v["count"], "%": v["percent"]} for k, v in dist.items()],
                use_container_width=True,
            )

    st.subheader("Exemple de prompt")
    if result.prompts:
        p = result.prompts[0]
        st.code(p.positive, language="text")
        st.caption("Prompt négatif")
        st.code(p.negative, language="text")
else:
    st.info("Réglez les paramètres dans la barre latérale puis cliquez sur « Générer ».")
