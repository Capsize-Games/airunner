from airunner.components.llm.managers.agent.actions.agent_action import AgentAction


class AnalyzeConversation(AgentAction):
    @staticmethod
    def run(llm, request):
        return llm.analyze_conversation(request)
