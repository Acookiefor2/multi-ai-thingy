# ⬡ Council

**One chat window. Every AI. Shared context.**

Council is a multi-LLM desktop chat app that lets Claude, GPT, and Gemini all share the same conversation history — so you never have to re-explain context when switching models.

---

## Install

```bash
pip install -r requirements.txt
python main.py
```

---

## Usage

| Command | What it does |
|---------|-------------|
| `@claude your message` | Send to Claude only |
| `@gpt your message` | Send to GPT only |
| `@gemini your message` | Send to Gemini only |
| `@all your message` | Broadcast to all configured models |
| No tag | Sends to the last model you used |

Every model sees the full conversation, including what the other models said (labeled `[CLAUDE]:`, `[GPT]:`, `[GEMINI]:`).

---

## Setup

Click **⚙ Keys** in the top-right corner and paste in your API keys:

- **Claude**: [console.anthropic.com](https://console.anthropic.com)
- **GPT**: [platform.openai.com](https://platform.openai.com)
- **Gemini**: [aistudio.google.com](https://aistudio.google.com)

You only need the keys for models you want to use. Council works fine with just one.

---

## Architecture

```
council/
├── main.py                    # Entry point
├── requirements.txt
├── core/
│   ├── context_manager.py     # Shared history store
│   ├── router.py              # @model tag parser
│   └── adapters/
│       ├── base.py            # Abstract base adapter
│       ├── claude.py          # Anthropic SDK
│       ├── openai_adapter.py  # OpenAI SDK
│       └── gemini.py          # Google Generative AI SDK
└── ui/
    └── app.py                 # PyQt5 GUI
```

---

## How context sharing works

Every message (user or AI) gets appended to a shared `ContextManager` history with a speaker tag. When you address a model, Council:

1. Grabs the full history
2. Formats it for that model's API schema
3. Injects a system prompt explaining the multi-agent setup
4. Sends the request
5. Tags the response `[MODEL]` and appends it back to shared history

So when you say `@gemini what do you think about claude's suggestion?` — Gemini literally sees Claude's previous message in its context.

---

Built by Acookiefor2.
