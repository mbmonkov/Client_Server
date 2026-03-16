import unittest
from app.captcha import MathCaptcha


class TestMathCaptcha(unittest.TestCase):

    def setUp(self):
        self.captcha = MathCaptcha()

    def test_generate_challenge_returns_tuple(self):
        result = self.captcha.generate_challenge()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_answer_is_string(self):
        _, answer = self.captcha.generate_challenge()
        self.assertIsInstance(answer, str)

    def test_mathematical_correctness(self):
        for _ in range(100):
            question, answer = self.captcha.generate_challenge()

            parts = question.replace("How is ", "").replace("?", "").split()
            num1 = int(parts[0])
            op = parts[1]
            num2 = int(parts[2])

            if op == '+':
                expected = num1 + num2
            else:
                expected = num1 - num2
                self.assertTrue(num1 >= num2)

            self.assertEqual(int(answer), expected)


    def test_randomness(self):
        results = set()
        for _ in range(50):
            results.add(self.captcha.generate_challenge())
        self.assertTrue(len(results) > 1)


if __name__ == '__main__':
    unittest.main()