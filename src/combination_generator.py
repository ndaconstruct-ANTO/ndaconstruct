"""Moteur de génération des combinaisons de traits.

Produit des personnages uniques (pelage × yeux × style × objet) de manière
reproductible grâce à une seed maître. Gère :
  - les traits autorisés (filtrage),
  - les combinaisons interdites,
  - l'unicité stricte (pas de doublon),
  - l'attribution d'identifiants séquentiels,
  - la dérivation d'une seed par image.

La rareté n'est PAS calculée ici : elle est ajoutée ensuite par rarity_engine,
afin de garder ce module concentré sur la combinatoire.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import utils


# ---------------------------------------------------------------------------
# Chargement et regroupement de toute la configuration
# ---------------------------------------------------------------------------
@dataclass
class ConfigBundle:
    """Regroupe toute la configuration chargée depuis les fichiers YAML."""

    collection: Dict[str, Any]
    fur_colors: List[Dict[str, Any]]
    eye_colors: List[Dict[str, Any]]
    styles: List[Dict[str, Any]]
    common_forbidden: List[str]
    default_shoes: str
    rarity: Dict[str, Any]
    forbidden: List[Dict[str, Any]]

    @classmethod
    def load(cls, collection_path: str = "config/collection.yaml") -> "ConfigBundle":
        collection = utils.load_yaml(collection_path)
        cfg_files = collection["config_files"]
        fur = utils.load_yaml(cfg_files["fur_colors"])["fur_colors"]
        eyes = utils.load_yaml(cfg_files["eye_colors"])["eye_colors"]
        styles_doc = utils.load_yaml(cfg_files["styles"])
        rarity = utils.load_yaml(cfg_files["rarity"])["rarity"]
        forbidden_doc = utils.load_yaml(cfg_files["forbidden_combinations"])
        return cls(
            collection=collection,
            fur_colors=fur,
            eye_colors=eyes,
            styles=styles_doc["styles"],
            common_forbidden=styles_doc.get("common_forbidden", []),
            default_shoes=styles_doc.get("default_shoes", "generic plain shoes"),
            rarity=rarity,
            forbidden=forbidden_doc.get("forbidden", []) or [],
        )

    # -- filtrage par traits autorisés --------------------------------------
    def allowed(self) -> "ConfigBundle":
        """Renvoie une copie filtrée selon allowed_traits de collection.yaml."""
        allow = self.collection.get("allowed_traits", {}) or {}

        def keep(items, keys):
            if not keys:
                return items
            kept = [it for it in items if it["key"] in keys]
            if not kept:
                raise ValueError(
                    f"Aucun trait ne correspond au filtre {keys}. Vérifiez allowed_traits."
                )
            return kept

        return ConfigBundle(
            collection=self.collection,
            fur_colors=keep(self.fur_colors, allow.get("fur_colors")),
            eye_colors=keep(self.eye_colors, allow.get("eye_colors")),
            styles=keep(self.styles, allow.get("styles")),
            common_forbidden=self.common_forbidden,
            default_shoes=self.default_shoes,
            rarity=self.rarity,
            forbidden=self.forbidden,
        )


# ---------------------------------------------------------------------------
# Représentation d'un personnage
# ---------------------------------------------------------------------------
@dataclass
class Character:
    """Un lionceau unique de la collection (avant rendu image)."""

    index: int
    id: str
    fur: Dict[str, Any]
    eyes: Dict[str, Any]                       # œil gauche (et droit si homochromie)
    style: Dict[str, Any]
    obj: Dict[str, Any]
    seed: int
    eyes_right: Optional[Dict[str, Any]] = None  # œil droit si hétérochromie (§7)
    rarity: Optional[Dict[str, Any]] = None
    rarity_score: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def left_eye(self) -> Dict[str, Any]:
        return self.eyes

    @property
    def right_eye(self) -> Dict[str, Any]:
        """Œil droit : identique au gauche sauf hétérochromie explicite."""
        return self.eyes_right or self.eyes

    @property
    def heterochromia(self) -> bool:
        """Vrai si les deux yeux ont des couleurs différentes (§7)."""
        return self.eyes_right is not None and self.eyes_right["key"] != self.eyes["key"]

    @property
    def combo_key(self) -> str:
        """Clé d'unicité d'une combinaison (sans la rareté, qui en découle).

        Reste identique à l'historique quand les deux yeux sont de même couleur ;
        n'inclut l'œil droit que lorsqu'il diffère (hétérochromie).
        """
        eyes_key = self.eyes["key"]
        if self.heterochromia:
            eyes_key = f"{self.eyes['key']}+{self.right_eye['key']}"
        return f"{self.fur['key']}|{eyes_key}|{self.style['key']}|{self.obj['key']}"

    def trait_dict(self) -> Dict[str, str]:
        """Dictionnaire simple {trait: clé} pour les règles interdites/rares."""
        return {
            "fur": self.fur["key"],
            "eyes": self.eyes["key"],
            "style": self.style["key"],
            "object": self.obj["key"],
        }


# ---------------------------------------------------------------------------
# Règles de combinaison interdite
# ---------------------------------------------------------------------------
def _rule_matches(rule_match: Dict[str, str], traits: Dict[str, str]) -> bool:
    """Vrai si TOUTES les clés de la règle correspondent aux traits du perso."""
    return all(traits.get(k) == v for k, v in rule_match.items())


def is_forbidden(traits: Dict[str, str], forbidden_rules: List[Dict[str, Any]]) -> bool:
    """Vrai si la combinaison correspond à au moins une règle interdite."""
    for rule in forbidden_rules:
        match = rule.get("match", {})
        if match and _rule_matches(match, traits):
            return True
    return False


# ---------------------------------------------------------------------------
# Tirage pondéré
# ---------------------------------------------------------------------------
def _weighted_choice(rng: random.Random, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tire un élément selon son rarity_weight (défaut 1 si absent)."""
    weights = [max(0.0001, float(it.get("rarity_weight", 1))) for it in items]
    return rng.choices(items, weights=weights, k=1)[0]


def _pick_object(rng: random.Random, style: Dict[str, Any]) -> Dict[str, Any]:
    """Choisit UN seul objet parmi ceux du style (règle de l'objet unique)."""
    objects = style.get("objects") or []
    if not objects:
        # Style sans objet : la patte reste vide.
        return {"key": "none", "name": "Aucun", "prompt": "no held object, both paws empty"}
    return rng.choice(objects)


# ---------------------------------------------------------------------------
# Générateur principal
# ---------------------------------------------------------------------------
class CombinationGenerator:
    """Génère une liste de personnages uniques et reproductibles."""

    def __init__(self, bundle: ConfigBundle):
        self.bundle = bundle.allowed()
        gen_cfg = self.bundle.collection.get("generation", {})
        self.master_seed = int(gen_cfg.get("master_seed", 0))
        self.enforce_unique = bool(gen_cfg.get("enforce_unique_combinations", True))
        self.max_attempts = int(gen_cfg.get("max_attempts_per_image", 2000))
        # Probabilité qu'un personnage ait deux yeux de couleurs différentes (§7).
        # 0.0 par défaut => collection homochromatique, séquence aléatoire inchangée.
        self.heterochromia_chance = float(gen_cfg.get("heterochromia_chance", 0.0))
        self.id_width = 4

    def max_unique_combinations(self) -> int:
        """Nombre théorique maximum de combinaisons uniques disponibles."""
        total = 0
        n_fur = len(self.bundle.fur_colors)
        n_eyes = len(self.bundle.eye_colors)
        for style in self.bundle.styles:
            n_obj = max(1, len(style.get("objects") or []))
            total += n_fur * n_eyes * n_obj
        return total

    def generate(self, count: int, *, existing_keys: Optional[set] = None) -> List[Character]:
        """Génère `count` personnages uniques.

        `existing_keys` permet de poursuivre une collection déjà commencée en
        évitant de réutiliser des combinaisons déjà créées (historique).
        """
        if count <= 0:
            return []

        # Garde-fou : on ne peut pas créer plus d'uniques que le maximum théorique.
        max_unique = self.max_unique_combinations()
        usable_forbidden = len(self.bundle.forbidden)  # estimation grossière
        if self.enforce_unique and count > max_unique:
            raise ValueError(
                f"Impossible de générer {count} combinaisons uniques : "
                f"le maximum théorique est {max_unique}. "
                f"Ajoutez des styles, des couleurs d'yeux, ou réduisez le nombre. "
                f"(Règles interdites définies : {usable_forbidden})"
            )

        rng = random.Random(self.master_seed)
        seen = set(existing_keys or set())
        start_index = (len(existing_keys) if existing_keys else 0) + 1

        characters: List[Character] = []
        produced = 0
        index = start_index

        while produced < count:
            character = self._draw_one(rng, index)
            attempts = 0
            while (
                self.enforce_unique
                and (
                    character.combo_key in seen
                    or is_forbidden(character.trait_dict(), self.bundle.forbidden)
                )
            ):
                attempts += 1
                if attempts > self.max_attempts:
                    raise RuntimeError(
                        "Trop de tentatives pour trouver une combinaison unique. "
                        "L'espace de combinaisons est probablement saturé. "
                        "Réduisez --count ou ajoutez des traits."
                    )
                character = self._draw_one(rng, index)

            # Cas où l'unicité n'est pas imposée : on évite quand même les interdites.
            if not self.enforce_unique and is_forbidden(
                character.trait_dict(), self.bundle.forbidden
            ):
                continue

            seen.add(character.combo_key)
            characters.append(character)
            produced += 1
            index += 1

        return characters

    def _draw_one(self, rng: random.Random, index: int) -> Character:
        """Tire une combinaison (sans garantir l'unicité — géré par l'appelant)."""
        fur = _weighted_choice(rng, self.bundle.fur_colors)
        eyes = _weighted_choice(rng, self.bundle.eye_colors)
        style = _weighted_choice(rng, self.bundle.styles)
        obj = _pick_object(rng, style)

        # Hétérochromie optionnelle (§7). Le court-circuit garantit qu'avec une
        # probabilité de 0 (défaut) aucun tirage supplémentaire n'est consommé :
        # la séquence aléatoire — donc toute la collection — reste inchangée.
        eyes_right = None
        if self.heterochromia_chance > 0 and rng.random() < self.heterochromia_chance:
            for _ in range(8):
                candidate = _weighted_choice(rng, self.bundle.eye_colors)
                if candidate["key"] != eyes["key"]:
                    eyes_right = candidate
                    break

        seed = utils.derive_seed(
            self.master_seed, fur["key"], eyes["key"], style["key"], obj["key"], index
        )
        return Character(
            index=index,
            id=utils.format_id(index, self.id_width),
            fur=fur,
            eyes=eyes,
            eyes_right=eyes_right,
            style=style,
            obj=obj,
            seed=seed,
        )
