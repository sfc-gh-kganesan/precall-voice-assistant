def main(sdk):
    message = sdk.get_parameter("message")
    print(f'[echo] Received: "{message}"')
    return {
        "echo": message,
        "reversed": message[::-1],
        "length": len(message),
    }
