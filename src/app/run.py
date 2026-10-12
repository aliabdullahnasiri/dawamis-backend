import uvicorn


def main() -> None:
    """
    Entry point to start the FastAPI application using Uvicorn.

    Configures the server to run on the local loopback address
    (127.0.0.1) and port 8000.
    """
    uvicorn.run(
        "app:main",
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()
