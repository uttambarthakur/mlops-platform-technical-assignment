import secrets


def main() -> None:
    print(f"SECRET_KEY={secrets.token_urlsafe(32)}")


if __name__ == "__main__":
    main()