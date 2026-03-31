# DSPy Data & I/O

## Data & Examples

```python
# dspy.Example — structured training/eval data
example = dspy.Example(question="What is DSPy?", answer="A framework for LM programming")

# Specify which fields are inputs
example = example.with_inputs("question")
print(example.inputs())   # {'question': ...}
print(example.labels())   # {'answer': ...}

# dspy.Prediction — module output container
pred = dspy.Prediction(answer="42", reasoning="step by step...")
print(pred.answer)

# Load built-in datasets
from dspy.datasets import HotPotQA, GSM8K, MATH
hotpotqa = HotPotQA(train_seed=2024, train_size=500)
trainset = hotpotqa.train
devset = hotpotqa.dev

gsm8k = GSM8K()                # grade-school math word problems
trainset = gsm8k.train          # fields: question, answer (numeric)

math_ds = MATH()                # competition-level math problems
trainset = math_ds.train        # fields: question, answer

# DataLoader — load custom datasets from various sources
from dspy.datasets import DataLoader
dl = DataLoader()

# From HuggingFace
dataset = dl.from_huggingface(
    "dataset_name",
    fields=["question", "answer"],
    input_keys=("question",),
    split="train"
)

# Also supports:
# dl.from_csv("data.csv", fields=["q", "a"], input_keys=("q",))
# dl.from_json("data.json", fields=["q", "a"], input_keys=("q",))
# dl.from_pandas(df, fields=["q", "a"], input_keys=("q",))
# dl.from_parquet("data.parquet", fields=["q", "a"], input_keys=("q",))
```

---

## Special Data Types

```python
# Images (multimodal)
class DescribeImage(dspy.Signature):
    image: dspy.Image = dspy.InputField()
    description: str = dspy.OutputField()

img_from_url = dspy.Image.from_url("https://example.com/image.jpg")
img_from_file = dspy.Image.from_file("local.png")
img_from_b64 = dspy.Image(url="data:image/png;base64,...")

# Audio
class TranscribeAudio(dspy.Signature):
    audio: dspy.Audio = dspy.InputField()
    transcript: str = dspy.OutputField()

audio = dspy.Audio.from_file("speech.mp3")

# Conversation History
class Chat(dspy.Signature):
    history: dspy.History = dspy.InputField()
    message: str = dspy.InputField()
    response: str = dspy.OutputField()

history = dspy.History(messages=[
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"},
])
```

---

## Save & Load

Two modes — state-only (recommended) vs full program:

```python
# State-only (JSON) — saves signatures, demos, LM per predictor
optimized_program.save("my_program.json")

# State-only (pickle) — needed when state contains non-JSON-serializable objects (e.g., dspy.Image)
optimized_program.save("my_program.pkl", save_program=False)

# Full program (architecture + state) — saves to directory via cloudpickle
optimized_program.save("./my_program_dir/", save_program=True)
# With custom modules that need to be serialized by value:
optimized_program.save("./my_program_dir/", save_program=True, modules_to_serialize=[my_module])

# Load state-only (requires re-instantiating the class)
loaded = MyProgramClass()
loaded.load("my_program.json")

# Load full program (architecture + state) — no need to re-define the class
loaded = dspy.load("./my_program_dir/")
# Returns a fully functional module with all state, signatures, demos, and LM config restored.
```

**Security:** `.pkl` files and `dspy.load()` use cloudpickle/pickle and can execute arbitrary code on load — only load from trusted sources.
