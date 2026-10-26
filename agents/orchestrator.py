"""
Multi-agent orchestrator using LangGraph + Groq (free, fast).
Routes messages to specialist agents via intent classification.
"""

import os
import json
from groq import Groq
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from prompts.prompt_templates import ORCHESTRATOR_SYSTEM_PROMPT, CHAT_ROUTER_PROMPT
from agents.profile_analyzer import ProfileAnalyzerAgent
from agents.job_fit_agent import JobFitAgent
from agents.content_enhancer import ContentEnhancerAgent
from agents.career_counselor import CareerCounselorAgent
from memory.memory_manager import MemoryManager

MODEL = "openai/gpt-oss-120b"


# ─────────────────────────────────────────────────────────────
# LangGraph State Schema
# ─────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    user_message: str
    intent: str
    extracted_info: dict
    profile_data: dict
    memory_context: dict
    agent_response: str


# ─────────────────────────────────────────────────────────────
# Groq helper
# ─────────────────────────────────────────────────────────────
def call_llm(prompt: str, system: str = "", history: list = None,
             max_tokens: int = 2048) -> str:
    """
    Call GPT-OSS 120B via Groq.
    Free tier: 14,400 requests/day, 500,000 tokens/day.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    if history:
        for msg in history[:-1]:
            role = msg.get("role", "user")
            # Groq only accepts 'user' or 'assistant'
            if role not in ("user", "assistant"):
                role = "user"
            messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )

    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────
class Orchestrator:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

        self.profile_analyzer = ProfileAnalyzerAgent()
        self.job_fit_agent = JobFitAgent()
        self.content_enhancer = ContentEnhancerAgent()
        self.career_counselor = CareerCounselorAgent()

        self.graph = self._build_graph()

    def _build_graph(self):
        wf = StateGraph(AgentState)

        wf.add_node("router", self._router_node)
        wf.add_node("profile_analyzer", self._profile_node)
        wf.add_node("job_fit", self._job_fit_node)
        wf.add_node("content_enhancer", self._content_node)
        wf.add_node("career_counselor", self._career_node)
        wf.add_node("general_chat", self._general_chat_node)
        wf.add_node("clarifier", self._clarifier_node)

        wf.set_entry_point("router")

        wf.add_conditional_edges("router", lambda s: s["intent"], {
            "PROFILE_ANALYSIS": "profile_analyzer",
            "JOB_FIT": "job_fit",
            "CONTENT_ENHANCE": "content_enhancer",
            "CAREER_GUIDANCE": "career_counselor",
            "GENERAL_CHAT": "general_chat",
            "FETCH_PROFILE": "general_chat",
            "CLARIFICATION_NEEDED": "clarifier",
        })

        for node in ["profile_analyzer", "job_fit", "content_enhancer",
                     "career_counselor", "general_chat", "clarifier"]:
            wf.add_edge(node, END)

        return wf.compile(checkpointer=self.memory.checkpointer)

    # ── Router ────────────────────────────────────────────────
    def _router_node(self, state: AgentState) -> AgentState:
        context = self.memory.get_full_context()

        prompt = CHAT_ROUTER_PROMPT.format(
            user_message=state["user_message"],
            has_profile=context["has_profile"],
            context=context["memory_context"][:400],
        )

        raw = call_llm(
            prompt=prompt,
            system="You are a router. Respond ONLY with valid JSON. No explanation, no markdown.",
            max_tokens=200,
        )

        try:
            clean = raw.strip()
            if "```" in clean:
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            result = json.loads(clean.strip())
        except Exception:
            result = {"intent": "GENERAL_CHAT", "extracted_info": {}}

        valid_intents = {
            "PROFILE_ANALYSIS", "JOB_FIT", "CONTENT_ENHANCE",
            "CAREER_GUIDANCE", "GENERAL_CHAT", "FETCH_PROFILE", "CLARIFICATION_NEEDED"
        }
        intent = result.get("intent", "GENERAL_CHAT")
        if intent not in valid_intents:
            intent = "GENERAL_CHAT"

        state["intent"] = intent
        state["extracted_info"] = result.get("extracted_info", {})
        state["memory_context"] = context
        state["profile_data"] = context.get("profile_data") or {}
        return state

    # ── Profile Analysis ──────────────────────────────────────
    def _profile_node(self, state: AgentState) -> AgentState:
        if not state.get("profile_data"):
            state["agent_response"] = (
                "I'd love to analyze your profile! Please upload your LinkedIn PDF "
                "using the sidebar (Profile → More → Save to PDF). 🔍"
            )
            return state
        state["agent_response"] = self.profile_analyzer.analyze(
            state["profile_data"], state["memory_context"]
        )
        return state

    # ── Job Fit ────────────────────────────────────────────────
    def _job_fit_node(self, state: AgentState) -> AgentState:
        if not state.get("profile_data"):
            state["agent_response"] = (
                "To analyze job fit, I first need your LinkedIn profile. "
                "Please upload your LinkedIn PDF in the sidebar! 🎯"
            )
            return state

        job_role = (
            state.get("extracted_info", {}).get("job_role")
            or state["user_message"]
        )
        company = state.get("extracted_info", {}).get("company", "")

        state["agent_response"] = self.job_fit_agent.analyze(
            state["profile_data"], job_role, company, state["memory_context"]
        )

        self.memory.session.add_career_goal(job_role)
        self.memory.session.add_analyzed_job(job_role)
        return state

    # ── Content Enhancement ────────────────────────────────────
    def _content_node(self, state: AgentState) -> AgentState:
        if not state.get("profile_data"):
            state["agent_response"] = (
                "To rewrite your profile sections, I need your profile data first. "
                "Please upload your LinkedIn PDF in the sidebar! ✍️"
            )
            return state

        extracted = state.get("extracted_info", {})
        state["agent_response"] = self.content_enhancer.enhance(
            profile_data=state["profile_data"],
            section=extracted.get("section", ""),
            target_role=extracted.get("job_role", ""),
            user_message=state["user_message"],
            memory_context=state["memory_context"],
        )
        return state

    # ── Career Counseling ──────────────────────────────────────
    def _career_node(self, state: AgentState) -> AgentState:
        extracted = state.get("extracted_info", {})
        target_role = extracted.get("job_role", "")
        if target_role:
            self.memory.session.add_career_goal(target_role)

        state["agent_response"] = self.career_counselor.counsel(
            profile_data=state.get("profile_data") or {},
            target_role=target_role,
            user_message=state["user_message"],
            memory_context=state["memory_context"],
        )
        return state

    # ── General Chat ───────────────────────────────────────────
    def _general_chat_node(self, state: AgentState) -> AgentState:
        ctx = state["memory_context"]
        system = ORCHESTRATOR_SYSTEM_PROMPT.format(
            profile_summary=ctx.get("profile_summary", "No profile loaded"),
            career_goals=ctx.get("career_goals", "Not specified"),
            memory_context=ctx.get("memory_context", "")[:600],
        )

        history = self.memory.get_messages_for_api()

        state["agent_response"] = call_llm(
            prompt=state["user_message"],
            system=system,
            history=history,
            max_tokens=1500,
        )
        return state

    # ── Clarifier ─────────────────────────────────────────────
    def _clarifier_node(self, state: AgentState) -> AgentState:
        ctx = state["memory_context"]
        system = ORCHESTRATOR_SYSTEM_PROMPT.format(
            profile_summary=ctx.get("profile_summary", "No profile loaded"),
            career_goals=ctx.get("career_goals", "Not specified"),
            memory_context=ctx.get("memory_context", "")[:400],
        )

        prompt = (
            f"The user said: '{state['user_message']}'\n\n"
            "Ask ONE friendly clarifying question. Suggest 2-3 options of what you can help with."
        )

        state["agent_response"] = call_llm(prompt, system=system, max_tokens=400)
        return state

    # ── Main entry point ──────────────────────────────────────
    def process_message(self, user_message: str, thread_id: str = "default") -> str:
        self.memory.add_user_message(user_message)

        initial: AgentState = {
            "user_message": user_message,
            "intent": "",
            "extracted_info": {},
            "profile_data": {},
            "memory_context": {},
            "agent_response": "",
        }

        config = {"configurable": {"thread_id": thread_id}}
        final = self.graph.invoke(initial, config=config)

        response = final.get("agent_response", "Something went wrong. Please try again.")
        self.memory.add_assistant_message(response)
        return response
