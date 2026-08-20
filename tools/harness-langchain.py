#!/usr/bin/env python3
"""Deterministic harness for langchain-chat (stubs http_post + call_model)."""
import types

path = "/home/m/git/rpi5-ai-yokto/layers/meta-ai/recipes-core/yokto-ai-menu/files/langchain-chat"
nsp = {"__name__": "lc", "__file__": path}
exec(compile(open(path).read(), path, "exec"), nsp)

# stub http_post (module global) - round1 tool_calls, round2 final
def fake_http_post(host, port, path, body, timeout=600):
    msgs = body["messages"]
    if msgs and msgs[-1]["role"] == "tool":
        return {"choices": [{"message": {"role": "assistant",
              "content": "HAMSTER:%s" % msgs[-1]["content"][:30]}}]}
    return {"choices": [{"message": {"role": "assistant", "content": "",
        "tool_calls": [{"id": "call_1", "type": "function",
            "function": {"name": "system_info", "arguments": "{}"}}]}}]}

nsp["http_post"] = fake_http_post
nsp["server_reachable"] = lambda host, port, timeout=2: True
nsp["call_model"] = (lambda host, port, model, messages, max_tokens, temperature,
                     system=None: "SUMMARY-PLACEHOLDER-kept-facts")
lc = types.SimpleNamespace(**nsp)

print("=== 1) chat_with_tools tool loop ===")
msgs = [{"role": "user", "content": "Use system_info then tell hostname."}]
out = lc.chat_with_tools("127.0.0.1", 8080, "x", msgs, None, 100, 0.3)
print("final content:", out)
print("OK" if out.startswith("HAMSTER") else "FAIL loop")
last = fake_http_post.__globals__ and None
# track whether tool result was injected - reuse np http capture via a wrapper
print()
print("=== 2) compact() ===")
lm = []
for i in range(6):
    lm.append({"role": "user", "content": "u%d" % i})
    lm.append({"role": "assistant", "content": "a%d" % i})
before = len(lm)
c = lc.compact("127.0.0.1", 8080, "x", lm, None, 100, 0.3)
print("compact %d -> %d msgs; c[0]=%s" % (before, len(c), c[0]["role"]))
print("system summary:", c[0]["role"] == "system")
print()
print("=== 3) est_tokens ===", lc.est_tokens(lm, None))
print()
print("=== 4) command help ===")
print("help lists compact/tools/info/search/fetch:",
      all(k in lc.HELP for k in ("compact", "tools", "info", "search", "fetch")))
print("DONE")