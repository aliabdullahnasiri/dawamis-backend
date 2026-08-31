import uvicorn

import app


def main() -> None:
    uvicorn.run(
        "app:main",
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()
