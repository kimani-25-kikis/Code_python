import random
import re
from datetime import datetime

class ChatBot:
    def __init__(self, name="PyBot"):
        self.name = name
        self.user_name = None
        self.responses = {
            "greeting": [
                "Hello! How can I help you today?",
                "Hi there! What's on your mind?",
                "Hey! Great to see you.",
            ],
            "farewell": [
                "Goodbye! Have a great day!",
                "See you later!",
                "Take care!",
            ],
            "thanks": [
                "You're welcome!",
                "Happy to help!",
                "Anytime!",
            ],
            "how_are_you": [
                "I'm running smoothly, thanks for asking!",
                "Doing great! How about you?",
                "All systems go! How are you?",
            ],
            "default": [
                "Interesting, tell me more.",
                "I see. Can you elaborate?",
                "Hmm, I'm not sure I understand. Could you rephrase?",
            ],
        }

        # Pattern -> intent mapping (regex, intent)
        self.patterns = [
            (r"\b(hi|hello|hey|greetings)\b", "greeting"),
            (r"\b(bye|goodbye|see ya|farewell|exit|quit)\b", "farewell"),
            (r"\b(thanks|thank you|thx)\b", "thanks"),
            (r"\b(how are you|how's it going|how do you do)\b", "how_are_you"),
            (r"\bmy name is (\w+)", "set_name"),
            (r"\bwhat('s| is) my name\b", "get_name"),
            (r"\bwhat('s| is) the time\b|\bcurrent time\b", "time"),
            (r"\bwhat('s| is) the date\b|\btoday's date\b", "date"),
            (r"\bhelp\b", "help"),
        ]

    def _match_intent(self, text):
        text_lower = text.lower()
        for pattern, intent in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
                return intent, match
        return None, None

    def _reply(self, intent):
        return random.choice(self.responses.get(intent, self.responses["default"]))

    def respond(self, message):
        if not message.strip():
            return "Say something and I'll respond!"

        intent, match = self._match_intent(message)

        if intent == "set_name":
            self.user_name = match.group(1).capitalize()
            return f"Nice to meet you, {self.user_name}!"
        elif intent == "get_name":
            return f"Your name is {self.user_name}." if self.user_name else "You haven't told me your name yet."
        elif intent == "time":
            return f"The current time is {datetime.now().strftime('%H:%M:%S')}."
        elif intent == "date":
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
        elif intent == "help":
            return ("I can chat, tell you the time/date, remember your name, "
                    "and respond to greetings. Try: 'My name is Alex' or 'What time is it?'")
        elif intent:
            return self._reply(intent)
        else:
            return self._reply("default")

    def run(self):
        print(f"\n{'='*50}")
        print(f"  🤖 {self.name} - Your Friendly Chatbot")
        print(f"  Type 'quit' or 'bye' to exit")
        print(f"{'='*50}\n")

        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                reply = self.respond(user_input)
                print(f"{self.name}: {reply}")

                if re.search(r"\b(quit|exit|bye|goodbye)\b", user_input.lower()):
                    break
            except (KeyboardInterrupt, EOFError):
                print(f"\n{self.name}: Goodbye!")
                break


if __name__ == "__main__":
    bot = ChatBot(name="PyBot")
    bot.run()