import os
from app.agent import AutonomousAgent
from app.config import settings

if __name__ == "__main__":

    os.makedirs(settings.WORKSPACE, exist_ok=True)

    agent = AutonomousAgent()

    task = input("Enter task for AI Engineer:\n> ")

    agent.run(task)