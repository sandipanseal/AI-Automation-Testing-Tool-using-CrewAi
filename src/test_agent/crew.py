import os
from dotenv import load_dotenv
from typing import List
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

from .tools.custom_tool import CustomPlaywrightTool
from .tools.custom_tool import StripTripleBackticksTool
from crewai.agents.agent_builder.base_agent import BaseAgent
import re

env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@playwright/mcp@latest", "--isolated"]
)

@CrewBase
class TestAutomationCrew:
    agents: List[BaseAgent]
    tasks: List[Task]

    mcp_adapter = MCPServerAdapter(server_params)
    playwright_tool_runner = CustomPlaywrightTool()
    strip_backticks_tool = StripTripleBackticksTool()

    @agent
    def app_explorer(self) -> Agent:
        return Agent(
            config=self.agents_config['app_explorer'],
            tools=self.mcp_adapter.tools,
            verbose=False,
            allow_delegation=False,
            reasoning=True
        )

    @agent
    def test_case_writer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_case_writer'],
            verbose=False,
            allow_delegation=True,
            reasoning=True
        )

    @agent
    def script_generator(self) -> Agent:
        return Agent(
            config=self.agents_config['script_generator'],
            tools=self.mcp_adapter.tools,
            verbose=False,
            allow_delegation=True,
            reasoning=True
        )

    @agent
    def test_executor(self) -> Agent:
        return Agent(
            config=self.agents_config['test_executor'],
            tools=[self.playwright_tool_runner] + list(self.mcp_adapter.tools),
            verbose=False,
            allow_delegation=True,
            multimodal=True,
            reasoning=True
        )
    
    @agent
    def post_processing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['post_processing_agent'],
            tools=[self.strip_backticks_tool],
            verbose=False,
            allow_delegation=False,
            reasoning=False
      )

    
    @task
    def exploration_task(self) -> Task:
        return Task(config=self.tasks_config['exploration_task'])
    
    @task
    def strip_exploration_backticks_task(self) -> Task:
        return Task(config=self.tasks_config['strip_exploration_backticks_task'])

    @task
    def test_case_writing_task(self) -> Task:
        return Task(config=self.tasks_config['test_case_writing_task'])
    
    @task
    def strip_testcases_backticks_task(self) -> Task:
        return Task(config=self.tasks_config['strip_testcases_backticks_task'])

    @task
    def script_generation_task(self) -> Task:
        return Task(config=self.tasks_config['script_generation_task'])
    
    @task
    def strip_testscript_backticks_task(self) -> Task:
        return Task(config=self.tasks_config['strip_testscript_backticks_task'])

    @task
    def test_execution_and_fix_task(self) -> Task:
        return Task(config=self.tasks_config['test_execution_and_fix_task'])

    @crew
    def crew(self) -> Crew:
        plan_only = os.environ.get("FAST_PLAN_ONLY") == "1"

        base_tasks = [
            self.exploration_task(),
            self.strip_exploration_backticks_task(),
            self.test_case_writing_task(),
            self.strip_testcases_backticks_task(),
        ]

        full_tasks = base_tasks + [
            self.script_generation_task(),
            self.strip_testscript_backticks_task(),
            self.test_execution_and_fix_task(),
        ]

        if plan_only:
            agents = [
                self.app_explorer(),
                self.post_processing_agent(),
                self.test_case_writer(),
                self.post_processing_agent(),
            ]
            tasks = base_tasks
        else:
            agents = [
                self.app_explorer(),
                self.post_processing_agent(),
                self.test_case_writer(),
                self.post_processing_agent(),
                self.script_generator(),
                self.post_processing_agent(),
                self.test_executor()
            ]
            tasks = full_tasks

        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
