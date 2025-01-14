# utils/json_to_markdown.py

def dict_to_markdown(d, indent=0):
    """
    Recursively converts a Python dictionary or list into a bullet-style Markdown.
    :param d: Dictionary (or list) to convert
    :param indent: Current indentation level
    :return: List of markdown lines
    """
    lines = []
    prefix = "  " * indent  # Two spaces per indent level

    if isinstance(d, dict):
        for key, value in d.items():
            if isinstance(value, dict) or isinstance(value, list):
                lines.append(f"{prefix}- **{key}**:")
                lines.extend(dict_to_markdown(value, indent + 1))
            else:
                lines.append(f"{prefix}- **{key}**: {value}")
    elif isinstance(d, list):
        for index, item in enumerate(d):
            if isinstance(item, dict) or isinstance(item, list):
                lines.append(f"{prefix}- **Item {index}**:")
                lines.extend(dict_to_markdown(item, indent + 1))
            else:
                lines.append(f"{prefix}- **Item {index}**: {item}")

    return lines

def json_to_markdown(resp_json):
    """
    Top-level function that takes a dict (parsed from JSON)
    and returns a well-structured Markdown string.
    """
    lines = ["# Zyte JSON Response\n"]
    lines.extend(dict_to_markdown(resp_json))
    return "\n".join(lines)
