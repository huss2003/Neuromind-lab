# Reference Patterns (illustrative, not production-complete)

## TypeScript submission result
```ts
export type SubmissionStatus = "queued" | "running" | "passed" | "failed" | "timeout" | "error";
export type SubmissionResult = {
  submission_id: string;
  status: SubmissionStatus;
  score: number | null;
  passed_tests: number;
  total_tests: number;
  execution_ms: number | null;
  feedback: Array<{ kind: "success" | "hint" | "error" | "info"; message: string }>;
};
```

## React async-state pattern
```tsx
type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "success"; data: T };

export function StatusPanel({ state }: { state: AsyncState<unknown> }) {
  if (state.status === "loading") return <p role="status">Loading…</p>;
  if (state.status === "error") return <section role="alert"><p>{state.message}</p><button onClick={state.retry}>Retry</button></section>;
  return <p>Ready</p>;
}
```

## FastAPI pattern
```python
from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/example")

class ExampleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ExampleResponse(BaseModel):
    message: str

@router.post("", response_model=ExampleResponse)
async def create_example(payload: ExampleRequest) -> ExampleResponse:
    # Add authentication, service layer, structured errors and tests.
    return ExampleResponse(message=f"Accepted {payload.name.strip()}")
```

## Pytest contract pattern
```python
def test_unknown_option_is_rejected(client, learner_token, checkpoint_id):
    response = client.post(
        f"/api/v1/checkpoints/{checkpoint_id}/attempts",
        headers={"Authorization": f"Bearer {learner_token}"},
        json={"question_id": "00000000-0000-0000-0000-000000000001", "selected_option_id": "invalid"},
    )
    assert response.status_code == 422
```

## Manifest sketch
```json
{
  "lecture_id": "demo-lecture-9",
  "content_version": 1,
  "segments": [
    {"id":"intro","order":1,"type":"video","title":"Introduction","media_provider":"r2","media_asset_key":"demo/lecture-09/01-intro.mp4","next_action":{"type":"next_segment"}},
    {"id":"mcq-1","order":2,"type":"checkpoint","title":"Knowledge check 1","checkpoint_id":"demo-checkpoint-1","next_action":{"type":"next_segment"}},
    {"id":"practical","order":3,"type":"video","title":"Practical demo","media_provider":"r2","media_asset_key":"demo/lecture-09/06-practical.mp4","exercise_id":"demo-exercise-9","next_action":{"type":"open_exercise"}}
  ]
}
```
Use UUIDs and server validation in real code. These snippets illustrate patterns only.
