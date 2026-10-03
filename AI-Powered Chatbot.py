import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AIChatBot:
    def __init__(self, model="gpt-4o-mini", system_prompt=None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.system_prompt = system_prompt or (
            "You are a friendly, concise, and helpful assistant. "
            "Keep responses under 3 sentences unless asked for detail."
        )
        self.history = [{"role": "system", "content": self.system_prompt}]

    def respond(self, message):
        self.history.append({"role": "user", "content": message})
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.7,
            )
            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            # Keep history manageable
            if len(self.history) > 21:
                self.history = [self.history[0]] + self.history[-20:]
            return reply
        except Exception as e:
            return f"Sorry, I hit an error: {e}"

    def run(self):
        print("\n🤖 AI Chatbot ready. Type 'quit' to exit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in {"quit", "exit", "bye"}:
                    print("Bot: Goodbye!")
                    break
                if not user_input:
                    continue
                print(f"Bot: {self.respond(user_input)}")
            except (KeyboardInterrupt, EOFError):
                print("\nBot: Goodbye!")
                break


if __name__ == "__main__":
    bot = AIChatBot()
    bot.run()