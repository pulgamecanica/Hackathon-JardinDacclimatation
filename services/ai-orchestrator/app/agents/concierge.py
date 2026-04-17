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
        "d'achat. Rappelle clairement qu'un billet simulé peut être modifié "
        "à tout moment, mais qu'un billet confirmé est irrévocable. "
        "Appelle les outils MCP pour tarifs et disponibilités plutôt que deviner."
    )
