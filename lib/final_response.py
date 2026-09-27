"""Recover one reasoning-only final response without treating reasoning as an answer."""
from copy import deepcopy


def reasoning_only_stop(body):
    choices = body.get("choices", [])
    if len(choices) != 1:
        return False
    choice = choices[0]
    message = choice.get("message", {})
    return (choice.get("finish_reason") == "stop"
            and not message.get("tool_calls")
            and not (message.get("content") or "").strip()
            and bool(message.get("reasoning_content") or message.get("reasoning")))


def combine_usage(first, second):
    """Count both requests, including cached input tokens, in the returned usage."""
    result = deepcopy(second)
    for key, value in first.items():
        if isinstance(value, dict):
            result[key] = combine_usage(value, result.get(key, {}))
        elif isinstance(value, (int, float)):
            result[key] = value + result.get(key, 0)
    return result


def complete(payload, send):
    """Return status, response and every raw attempt; at most two upstream calls."""
    status, body = send(payload)
    attempts = [{"phase": "original", "request": deepcopy(payload), "status": status, "response": deepcopy(body)}]
    if status != 200 or not reasoning_only_stop(body):
        return status, body, attempts

    recovery = deepcopy(payload)
    recovery["messages"].append({"role": "user", "content": (
        "Provide the requested final review using the evidence already returned by the tools. "
        "Write the answer for the portfolio manager, within the original word limit. "
        "If evidence is missing, state what is missing. Return the answer as ordinary assistant "
        "content, without internal reasoning or further tool calls.")})
    recovery.setdefault("chat_template_kwargs", {})["enable_thinking"] = False
    if recovery.get("tools"):
        recovery["tool_choice"] = "none"
    retry_status, retry_body = send(recovery)
    attempts.append({"phase": "final_answer_recovery", "request": recovery,
                     "status": retry_status, "response": deepcopy(retry_body)})
    choices = retry_body.get("choices", [])
    valid = (retry_status == 200 and len(choices) == 1
             and choices[0].get("finish_reason") == "stop"
             and not choices[0].get("message", {}).get("tool_calls")
             and bool((choices[0].get("message", {}).get("content") or "").strip()))
    if not valid:
        return 502, {"error": {"type": "final_answer_missing", "message":
                    "Local model did not produce a final answer after one recovery attempt."}}, attempts
    result = deepcopy(retry_body)
    result["usage"] = combine_usage(body.get("usage", {}), retry_body.get("usage", {}))
    return 200, result, attempts
