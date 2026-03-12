import json
from urllib import request, error


BASE_URL = "https://app-review-genai-project-production.up.railway.app"


def call(path: str) -> None:
    url = f"{BASE_URL}{path}"
    print(f"\n=== GET {url}")
    try:
        with request.urlopen(url, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            print(f"Status: {resp.status}")
            try:
                parsed = json.loads(body)
                print("JSON response:")
                print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                print("Raw response:")
                print(body)
    except error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        try:
            body = e.read().decode("utf-8")
            print("Error body:")
            print(body)
        except Exception:
            pass
    except error.URLError as e:
        print(f"URLError: {e.reason}")


def main() -> None:
    # Basic health check
    call("/api/health")
    # Latest pulse metadata (may return 'not_run' if no runs yet)
    call("/api/pulse/latest")


if __name__ == "__main__":
    main()

