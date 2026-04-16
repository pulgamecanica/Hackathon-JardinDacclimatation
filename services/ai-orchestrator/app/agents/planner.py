from app.agents.base import BaseAgent


class PlanningAgent(BaseAgent):
    """Builds day-of itineraries given date, party, and known tickets.

    Works identically whether tickets are simulated (planning) or purchased
    (already committed) — see project_ai_strategy.md.
    """

    task = "planning"
    system_prompt = (
        "Tu es Plume en mode PLANIFICATION. "
        "À partir de la date de visite, de la composition du groupe et des événements/fermetures "
        "obtenus via les outils MCP, propose un itinéraire réaliste. "
        "Tu aides aussi bien les utilisateurs qui ont déjà acheté leurs billets que ceux qui "
        "explorent une date en simulation — n'attends jamais d'achat pour proposer un plan."
    )
