# CAPTCHA Solver

`captcha_solver` is a Python package that provides a single interface for solving supported CAPTCHA types. The caller provides a CAPTCHA type and its content; the package selects the corresponding adapter and returns its prediction. Callers do not need to import or manage individual adapters.

The package currently includes an **image** CAPTCHA adapter backed by an OCR model. Additional types can be added as separate adapter folders.

## Usage

Place the `captcha_solver/` package in your project's Python import path, with the dependencies required by its installed adapters available in the Python environment.

```python
from captcha_solver import Captcha_Solver

# Create once and reuse for subsequent requests.
solver = Captcha_Solver()

with open("captcha.png", "rb") as file:
    captcha_data = file.read()

solution = solver.solve("image", captcha_data)
print(solution)
```

### Public API

**`Captcha_Solver()`** creates the public solver and initializes its factory and discovered adapters.

**`solver.solve(captcha_type: str, data: bytes) -> str`** accepts:

- `captcha_type`: The registered type identifier (currently `"image"`). The caller specifies the type; the package does not detect it automatically.
- `data`: The CAPTCHA content as bytes. For the image adapter, supply the raw image file bytes.

It returns the selected adapter's predicted solution as a string, assuming the adapter's model returns a string. An unregistered type raises `ValueError`. Model loading and inference failures are propagated from the adapter.

**Reuse the same `Captcha_Solver` instance** when solving multiple CAPTCHAs. The factory retains its adapter instances, so the image OCR model is loaded during initialization and reused for subsequent calls rather than being loaded for every CAPTCHA. Each independent solver instance creates its own adapters; separate server worker processes generally hold separate model instances.

## How It Works

### Package structure

```text
captcha_solver/
├── __init__.py
├── CAPTCHA_Solver.py
├── CAPTCHA_Solver_Interface.py
├── solver_factory.py
└── adapters/
    ├── __init__.py
    └── image/
        ├── __init__.py
        ├── solver.py
        ├── ocr_module.py
        └── captcha_model.pt
```

Other adapter folders can be added alongside `image/`. Python-generated `__pycache__/` folders are omitted.

| Component | Purpose |
| --- | --- |
| `captcha_solver/__init__.py` | Exposes `Captcha_Solver` as the package's public entry point. |
| `CAPTCHA_Solver.py` | Receives the requested type and content, then delegates to the factory-selected adapter. |
| `CAPTCHA_Solver_Interface.py` | Defines the abstract `solve(data)` contract that concrete adapters implement. |
| `solver_factory.py` | Discovers, validates, initializes, and stores the available adapters; looks them up by CAPTCHA type. |
| `adapters/<type>/` | Contains an adapter's implementation, dependencies, and model files. |

### Request flow

1. A caller creates `Captcha_Solver()`.
2. The factory discovers adapter packages under `captcha_solver.adapters` and registers their CAPTCHA types and solver instances.
3. The caller invokes `solver.solve(captcha_type, data)`.
4. The public solver asks the factory for the adapter registered to that type.
5. The adapter processes the bytes using its own model and returns the predicted solution.
6. The public solver returns that result to the caller.

The factory **routes using the type supplied by the caller**; it does not classify or infer the CAPTCHA type.

### Adding or replacing an adapter

Each adapter is a self-contained Python package inside `captcha_solver/adapters/`. To add a type, create an adapter folder containing at least:

```text
adapters/
└── example/
    ├── __init__.py
    └── solver.py
```

Implement the common interface in `solver.py`:

```python
from captcha_solver.CAPTCHA_Solver_Interface import Captcha_Solver_Interface


class ExampleSolver(Captcha_Solver_Interface):
    def solve(self, data: bytes) -> str:
        # Replace with this adapter's processing and inference.
        raise NotImplementedError
```

Declare the type and its implementation in the adapter's `__init__.py`:

```python
from .solver import ExampleSolver

CAPTCHA_TYPE = "example"
SOLVER_CLASS = ExampleSolver
```

The factory discovers these declarations when a new `Captcha_Solver` is initialized. No caller-side change is required beyond passing `"example"` as the CAPTCHA type. Keep any model weights, preprocessing, and type-specific code inside the adapter folder. Resolve model paths relative to the adapter's file location, not the process's current working directory.

To remove an adapter, remove its folder. To update an adapter, modify only its implementation or model files. **Restart running processes** after changes so the factory and any cached models are reinitialized.

### Design boundaries

- **Public solver:** stable entry point for application code.
- **Factory:** adapter discovery, registration, and lookup.
- **Abstract interface:** shared behavior contract for adapters.
- **Adapters:** CAPTCHA-type-specific preprocessing, model loading, and inference.

This separation lets callers depend on one package API while individual adapters can be added, removed, or modified independently. Adapter folders should contain trusted code, because automatic discovery imports and initializes them.
