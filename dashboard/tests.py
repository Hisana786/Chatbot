import json

from django.test import TestCase


class ChatbotApiTests(TestCase):
    def test_chat_api_returns_reply(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "How is stock today?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("reply", payload)
        self.assertTrue(payload["reply"])

    def test_chat_api_requires_message(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
