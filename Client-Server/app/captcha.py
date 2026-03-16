import random


class MathCaptcha:
    def generate_challenge(self):
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operators = ['+', '-']
        op = random.choice(operators)

        if op == '+':
            answer = num1 + num2
        else:
            num1, num2 = max(num1, num2), min(num1, num2)
            answer = num1 - num2

        question = f"{num1} {op} {num2}"
        return question, str(answer)
