
from flask import Flask, render_template, request, jsonify
import ast
import math
import operator
import re

app = Flask(__name__)

# -------------------------------
# Calculator configuration
# -------------------------------

MAX_EXPRESSION_LENGTH = 250
MAX_POWER = 100

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau
}


# -------------------------------
# Scientific functions
# Trigonometry uses degrees
# -------------------------------

def sin_deg(x):
    return math.sin(math.radians(x))

def cos_deg(x):
    return math.cos(math.radians(x))

def tan_deg(x):
    return math.tan(math.radians(x))

def asin_deg(x):
    return math.degrees(math.asin(x))

def acos_deg(x):
    return math.degrees(math.acos(x))

def atan_deg(x):
    return math.degrees(math.atan(x))

def cbrt(x):
    return math.copysign(abs(x) ** (1 / 3), x)


FUNCTIONS = {
    "sqrt": math.sqrt,
    "cbrt": cbrt,
    "sin": sin_deg,
    "cos": cos_deg,
    "tan": tan_deg,
    "asin": asin_deg,
    "acos": acos_deg,
    "atan": atan_deg,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "factorial": math.factorial,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round
}


# -------------------------------
# Safe mathematical evaluator
# -------------------------------

def evaluate(node, steps):

    if isinstance(node, ast.Expression):
        return evaluate(node.body, steps)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Invalid number")

    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ValueError("Unknown constant: " + node.id)

    if isinstance(node, ast.UnaryOp):
        operation = UNARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Invalid unary operator")

        value = evaluate(node.operand, steps)
        answer = operation(value)

        steps.append(f"Apply sign: {answer}")
        return answer

    if isinstance(node, ast.BinOp):
        left = evaluate(node.left, steps)
        right = evaluate(node.right, steps)

        operation = BINARY_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError("Unsupported operator")

        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
            raise ValueError("Power is too large")

        answer = operation(left, right)

        steps.append(f"{left} {type(node.op).__name__} {right} = {answer}")
        return answer

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Invalid function")

        name = node.func.id
        function = FUNCTIONS.get(name)

        if function is None:
            raise ValueError("Unknown function: " + name)

        if node.keywords:
            raise ValueError("Invalid function arguments")

        arguments = [evaluate(arg, steps) for arg in node.args]

        if len(arguments) != 1:
            raise ValueError("This function needs one argument")

        answer = function(arguments[0])
        steps.append(f"{name}({arguments[0]}) = {answer}")

        return answer

    raise ValueError("Invalid mathematical expression")


# -------------------------------
# Convert spoken expressions
# -------------------------------

def prepare_expression(expression):

    expression = expression.lower().strip()

    replacements = {
        "multiplied by": "*",
        "multiply by": "*",
        "divided by": "/",
        "divide by": "/",
        "to the power of": "**",
        "squared": "**2",
        "cubed": "**3",
        "square root of": "sqrt",
        "plus": "+",
        "minus": "-",
        "times": "*",
        "into": "*",
        "over": "/",
        "×": "*",
        "÷": "/",
        "−": "-",
        "^": "**"
    }

    for old, new in replacements.items():
        expression = expression.replace(old, new)

    # Convert 5 x 6 to 5 * 6
    expression = re.sub(
        r"(?<=\d)\s*x\s*(?=\d)",
        "*",
        expression
    )

    expression = expression.replace(" ", "")

    # Convert percentage values
    expression = re.sub(
        r"(\d+(?:\.\d+)?)%",
        r"(\1/100)",
        expression
    )

    return expression


# -------------------------------
# Validate expression
# -------------------------------

def validate_expression(expression):

    if not expression:
        raise ValueError("Please enter a calculation")

    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("Calculation is too long")

    allowed = r"[0-9a-zA-Z_+\-*/().,%]*"

    if not re.fullmatch(allowed, expression):
        raise ValueError("Invalid characters in calculation")


# -------------------------------
# Main calculator function
# -------------------------------

def calculate_expression(expression):

    expression = prepare_expression(expression)

    validate_expression(expression)

    steps = []

    tree = ast.parse(expression, mode="eval")

    result = evaluate(tree, steps)

    if isinstance(result, complex):
        raise ValueError("Complex results are not supported")

    if not math.isfinite(result):
        raise ValueError("Result is not finite")

    if isinstance(result, float) and result.is_integer():
        result = int(result)

    return result, steps


# -------------------------------
# Website home page
# -------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------------------
# Calculation API
# -------------------------------

@app.route("/calculate", methods=["POST"])
def calculate():

    try:

        data = request.get_json(silent=True) or {}

        expression = (
            data.get("expression")
            or data.get("calculation")
            or data.get("input")
            or data.get("text")
            or request.form.get("expression")
            or request.form.get("calculation")
            or request.form.get("input")
            or request.form.get("text")
            or ""
        )

        if not isinstance(expression, str):
            raise ValueError("Calculation must be text")

        if not expression.strip():
            raise ValueError("Please enter a calculation")

        result, steps = calculate_expression(expression)

        return jsonify({
            "success": True,
            "expression": expression,
            "result": result,
            "steps": steps
        })

    except ZeroDivisionError:

        return jsonify({
            "success": False,
            "error": "Cannot divide by zero"
        }), 400

    except OverflowError:

        return jsonify({
            "success": False,
            "error": "Number is too large"
        }), 400

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error) or "Invalid calculation"
        }), 400


# -------------------------------
# Health check
# -------------------------------

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "calculator": "Rishav's Calculator"
    })


# -------------------------------
# Start server
# -------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
