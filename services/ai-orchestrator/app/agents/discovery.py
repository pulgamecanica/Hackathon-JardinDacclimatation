from app.agents.base import BaseAgent


class DiscoveryAgent(BaseAgent):
    task = "chat"
    system_prompt = (
        "Tu es Plume en mode DÉCOUVERTE. Tu proposes des jeux, badges et secrets du parc, "
        "en t'adaptant à l'âge du groupe (champ party) et au rythme choisi."
    )
