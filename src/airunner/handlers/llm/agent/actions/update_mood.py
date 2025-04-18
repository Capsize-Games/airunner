from airunner.handlers.llm.agent.actions.agent_action import AgentAction


class UpdateMood(AgentAction):
    @staticmethod
    def run(llm, request):
        return llm.update_mood(request)
