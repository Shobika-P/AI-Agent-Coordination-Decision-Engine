from agents.business_decision_engine import business_decision_engine


def main():

    print()
    print("=" * 60)
    print("        AI BUSINESS DECISION ENGINE")
    print("        MULTI-AGENT BUSINESS DECISION ENGINE")
    print("=" * 60)

    task = input("\nEnter your business decision problem:\n> ")

    print("\nProcessing business decision...")
    print("Please wait...\n")

    result = business_decision_engine(task)

    print("=" * 60)
    print("              BUSINESS DECISION REPORT")
    print("=" * 60)
    print()

    print(result)

    print()
    print("=" * 60)
    print("                 END OF REPORT")
    print("=" * 60)


if __name__ == "__main__":
    main()