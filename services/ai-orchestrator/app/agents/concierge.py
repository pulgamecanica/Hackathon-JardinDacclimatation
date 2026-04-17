from app.agents.base import PAVO_PERSONA, BaseAgent


class ConciergeAgent(BaseAgent):
    task = "concierge"
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
        "billet confirmé est irrévocable."
    )
