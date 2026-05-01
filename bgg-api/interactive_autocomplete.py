#!/usr/bin/env python3

def main():
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import Completer, Completion
    except Exception:
        print("prompt_toolkit is required. Install with: pip install prompt_toolkit")
        return

    from boardgame_db import BoardGameDB

    db = BoardGameDB()

    class SimpleCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            text = text.strip()
            # if len(text) < 4:
            #     return
            for match, score in db.autocomplete_search(text, n=10) or []:
                yield Completion(match, start_position=-len(text))

    session = PromptSession(completer=SimpleCompleter(), complete_while_typing=True)
    try:
        while True:
            session.prompt("Search: ")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
