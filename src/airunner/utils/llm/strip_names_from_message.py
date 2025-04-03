def strip_names_from_message(
    message: str, 
    username: str, 
    botname: str
) -> str:
    """
    Removes names from start of message.
    """
    if message.startswith(f"{botname}: "):
        message = message[len(f"{botname}: "):]
    if message.startswith(f"{username}: "):
        message = message[len(f"{username}: "):]
    return message
