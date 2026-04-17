from __future__ import annotations

from typing import AsyncGenerator

from app.agents.base import PAVO_PERSONA, BaseAgent, SessionContext
from app.agents.packs import suggest_packs


class ConciergeAgent(BaseAgent):
    task = "concierge"
    facts_mode = "concierge"
    suggestions = [
        "Simuler des billets",
        "Tarifs adultes/enfants",
        "Confirmer mon achat",
    ]
    system_prompt = (
        f"{PAVO_PERSONA}\n\n"
        "MODE CONCIERGERIE. Tu assistes pour la billetterie : simulation, "
        "choix du bon billet selon la composition du groupe, confirmation "
        "d'achat. Utilise uniquement les tarifs et formules listés dans le "
        "contexte système — n'invente jamais un prix. Rappelle clairement "
        "qu'un billet simulé peut être modifié à tout moment, mais qu'un "
        "billet confirmé est irrévocable.\n\n"
        "Le système affiche automatiquement sous ta réponse 2 à 3 'packs' "
        "cliquables (déjà calculés à partir du catalogue). Ne recopie pas "
        "les prix ni les détails des packs dans ta réponse : présente-les "
        "brièvement (« voici quelques formules adaptées à votre groupe »), "
        "invite l'utilisateur à choisir celle qui lui parle, et indique "
        "qu'il peut toujours demander une alternative."
    )

    async def _extra_chunks(self, ctx: SessionContext) -> AsyncGenerator[dict, None]:
        offers = suggest_packs(ctx)
        if offers:
            yield {"type": "packs", "items": [o.to_dict() for o in offers]}
