from app.agents.base import PAVO_PERSONA, BaseAgent


class CompanionAgent(BaseAgent):
    task = "companion"
    suggestions = [
        "Où sont les toilettes ?",
        "Adapté aux enfants ?",
        "Horaires des attractions",
    ]
    system_prompt = (
        f"{PAVO_PERSONA}\n\n"
        "MODE COMPAGNON. Tu réponds aux questions pratiques pendant la visite : "
        "où trouver X, est-ce adapté aux enfants, horaires d'une attraction, "
        "toilettes, points de repos. Si une info dépend du jour ou de l'heure, "
        "appelle un outil MCP plutôt que deviner."
    )
