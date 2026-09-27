import unittest
from copy import deepcopy
from unittest.mock import Mock
from lib.final_response import complete


def response(content='', reasoning='', finish='stop', calls=None, tokens=10):
    return {'choices': [{'finish_reason': finish, 'message': {'content': content,
            'reasoning_content': reasoning, 'tool_calls': calls}}],
            'usage': {'prompt_tokens': tokens, 'completion_tokens': tokens,
                      'total_tokens': tokens * 2, 'prompt_tokens_details': {'cached_tokens': tokens - 1}}}


class FinalResponseTests(unittest.TestCase):
    def setUp(self):
        self.payload = {'messages': [{'role': 'user', 'content': 'Review the portfolio.'}],
                        'tools': [{'type': 'function'}], 'chat_template_kwargs': {'enable_thinking': True}}

    def test_reasoning_is_not_promoted_and_both_requests_are_counted(self):
        original = deepcopy(self.payload)
        send = Mock(side_effect=[(200, response(reasoning='private reasoning')),
                                 (200, response(content='Research must be refreshed.', tokens=20))])
        status, body, attempts = complete(self.payload, send)
        self.assertEqual(status, 200)
        self.assertEqual(body['choices'][0]['message']['content'], 'Research must be refreshed.')
        self.assertEqual(body['usage']['total_tokens'], 60)
        self.assertEqual(body['usage']['prompt_tokens_details']['cached_tokens'], 28)
        self.assertEqual(self.payload, original)
        correction = send.call_args.args[0]
        self.assertFalse(correction['chat_template_kwargs']['enable_thinking'])
        self.assertEqual(correction['tool_choice'], 'none')
        self.assertNotIn('private reasoning', str(correction))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]['response']['choices'][0]['message']['reasoning_content'], 'private reasoning')

    def test_second_empty_answer_is_explicit_failure_without_reasoning(self):
        send = Mock(return_value=(200, response(reasoning='private reasoning')))
        status, body, attempts = complete(self.payload, send)
        self.assertEqual(status, 502)
        self.assertEqual(send.call_count, 2)
        self.assertNotIn('private reasoning', str(body))
        self.assertEqual(len(attempts), 2)

    def test_tool_calls_visible_answers_and_length_stops_are_unchanged(self):
        for body in [response(content='Done.'), response(reasoning='Plan', calls=[{'id': 'x'}], finish='tool_calls'),
                     response(reasoning='Partial', finish='length')]:
            send = Mock(return_value=(200, body))
            status, result, attempts = complete(self.payload, send)
            self.assertEqual(result, body)
            send.assert_called_once()

    def test_recovery_must_finish_without_tools_or_truncation(self):
        for body in [response(content='Partial', finish='length'),
                     response(content='Calling tool', calls=[{'id': 'x'}])]:
            send = Mock(side_effect=[(200, response(reasoning='Plan')), (200, body)])
            self.assertEqual(complete(self.payload, send)[0], 502)

    def test_upstream_error_does_not_trigger_recovery(self):
        send = Mock(return_value=(400, {'error': 'Invalid request'}))
        self.assertEqual(complete(self.payload, send)[0], 400)
        send.assert_called_once()
