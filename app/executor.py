from app.tools import Tools


class Executor:

    @staticmethod
    def execute(action: str, tool_input: dict):

        if not action:
            return "No action provided."

        # Normalize tool input keys
        normalized = Executor.normalize_keys(tool_input)

        if action == "plan":
            return tool_input.get("files", [])
        
        if action == "write_file":
            return Tools.write_file(**normalized)

        if action == "read_file":
            return Tools.read_file(**normalized)

        if action == "run_shell":
            return Tools.run_shell(**normalized)

        if action == "finish":
            return normalized.get("message", "")

        return f"Unknown action: {action}"

    @staticmethod
    def normalize_keys(tool_input: dict):
        """
        Convert common wrong parameter names into correct ones.
        Example:
            filename -> path
        """
        if not tool_input:
            return {}

        normalized = dict(tool_input)

        # Fix common mistakes
        if "filename" in normalized and "path" not in normalized:
            normalized["path"] = normalized.pop("filename")

        return normalized