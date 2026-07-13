from agents.research_agent import research_agent
from agents.planning_agent import planning_agent


def main():
    print("=" * 50)
    print(" AI Agent Coordination & Decision Engine ")
    print("=" * 50)

    print("\nChoose an AI Agent:")
    print("1. Research Agent")
    print("2. Planning Agent")
    print("3. Coordination Agent")

    choice = input("\nEnter your choice (1 or 2 or 3): ")

    if choice == "1":
        question = input("\nEnter your research question: ")
        answer = research_agent(question)

        print("\nResearch Agent Response:\n")
        print(answer)

    elif choice == "2":
        task = input("\nEnter your planning task: ")
        answer = planning_agent(task)

        print("\nPlanning Agent Response:\n")
        print(answer)

    elif choice == "3":
        task = input("\nEnter your task: ")

        from agents.coordination_agent import coordination_agent

        answer = coordination_agent(task)

        print(answer)    
  
    else:
        print("Invalid Choice")


if __name__ == "__main__":
    main()

    