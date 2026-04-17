from app.agents.base import PAVO_PERSONA, BaseAgent


class PlanningAgent(BaseAgent):
    """Builds day-of itineraries given date, party, and known tickets.

    Works identically whether tickets are simulated (planning) or purchased
    (already committed) — see project_ai_strategy.md.
    """

    task = "planning"
    suggestions = [
        "Plan optimisé matinée",
        "Pause déjeuner",
        "Itinéraire pour ma date",
    ]
    system_prompt = (
        f"{PAVO_PERSONA}\n\n"
        "MODE PLANIFICATION. Propose un itinéraire court (3 à 5 étapes clés) "
        "adapté à la composition du groupe et à la date. Utilise uniquement "
        "les horaires, attractions et événements fournis dans le contexte "
        "système — n'invente rien. Tu aides aussi bien les visiteurs en "
        "simulation que ceux ayant acheté leurs billets ; n'attends jamais "
        "un achat pour planifier."
    )
