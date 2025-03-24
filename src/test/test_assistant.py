import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
import traceback

def create_test_assistant() -> Optional['Assistant']:
    try:
        from chatbot.assistant import Assistant
        return Assistant()
    except ImportError as e:
        traceback.print_tb(e.__traceback__)
        print(f"Error importing Assistant: {e}")
        print("Please ensure the Assistant class is properly imported")
        return None

def interactive_chat():
    """
    Simple interactive chat loop to test the Assistant functionality
    """
    assistant = create_test_assistant()
    if not assistant:
        sys.exit(1)

    print("=== Assistant Test Chat ===")
    print("Type 'quit' or 'exit' to end the conversation")
    print("Type 'clear' to start a new conversation")
    print("================================")

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
            
            # Check for clear command
            if user_input.lower() == 'clear':
                print("\n=== Starting New Conversation ===")
                assistant = create_test_assistant()
                continue
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Get response from assistant
            response_generator = assistant.generate_stream_response(user_input)
            for response in response_generator:
                print("\nAssistant:", response, end="", flush=True)
            print() # Add newline at end

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Try again or type 'exit' to quit")

if __name__ == "__main__":
    interactive_chat() 