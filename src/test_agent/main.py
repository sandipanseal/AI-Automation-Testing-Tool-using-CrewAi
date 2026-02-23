import asyncio
import sys
import os
from test_agent.crew import TestAutomationCrew

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run():
    def _read(prompt: str, env_key: str) -> str:
        val = os.getenv(env_key)
        if val and val.strip():
            print(f"{prompt}{val.strip()}")
            return val.strip()
        return input(prompt)

    application_url   = _read("Enter application URL: ", "APP_URL")
    test_name         = _read("Enter test name: ", "TEST_NAME")
    test_description  = _read("Enter test description: ", "TEST_DESC")

    inputs = dict(
        application_url=application_url,
        test_name=test_name,
        test_description=test_description
    )

    crew = TestAutomationCrew().crew()
    result = crew.kickoff(inputs=inputs)

    print("\n=== Final Report ===\n")
    print(result.raw)
    print("\nSaved as output/final_report.md")

if __name__ == "__main__":
    run()
