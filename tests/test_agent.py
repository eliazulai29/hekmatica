
import unittest
from Hekmatica.agent import Agent

class TestAgent(unittest.TestCase):
    def setUp(self):
        self.agent = Agent('Hekmatica/baml_src/clients.baml')

    def test_load_clients(self):
        clients = self.agent.load_clients('Hekmatica/baml_src/clients.baml')
        self.assertIsNotNone(clients)
        self.assertIn('client1', clients)

    def test_process_request_search(self):
        response = self.agent.process_request('client1', 'What is AI?')
        self.assertIsNotNone(response)

    def test_process_request_recommend(self):
        response = self.agent.process_request('client2', 'science fiction books')
        self.assertIsNotNone(response)

    def test_invalid_client(self):
        with self.assertRaises(ValueError):
            self.agent.process_request('invalid_client', 'query')

    def test_unsupported_feature(self):
        with self.assertRaises(NotImplementedError):
            self.agent.process_request('client1', 'query', 'unsupported_feature')

if __name__ == '__main__':
    unittest.main()
