def get_tool_declarations():
    return [
        {
            "name": "set_mode",
            "description": "Switch robot control mode between tracking, command, and intro.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "mode": {"type": "STRING", "enum": ["tracking", "command", "intro"]},
                },
                "required": ["mode"],
            },
        },
        {
            "name": "set_tracking",
            "description": "Enable or disable automatic face/motion tracking.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "enabled": {"type": "BOOLEAN"},
                },
                "required": ["enabled"],
            },
        },
        {
            "name": "look_direction",
            "description": "Move the robot gaze to a direction.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "direction": {
                        "type": "STRING",
                        "enum": ["left", "right", "up", "down", "center"],
                    },
                    "strength": {
                        "type": "INTEGER",
                        "description": "20-160 intensity",
                    },
                },
                "required": ["direction"],
            },
        },
        {
            "name": "move_head",
            "description": "Move head servos directly using calibrated pulse values.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "yaw": {"type": "INTEGER", "description": "CH8 range 1260-1840"},
                    "pitch": {"type": "INTEGER", "description": "CH7 range 1280-1700"},
                    "tilt": {"type": "INTEGER", "description": "CH9 range 1320-1680"},
                    "duration_s": {"type": "NUMBER", "description": "Hold time in seconds 0.2-4.0"},
                },
            },
        },
        {
            "name": "center_servos",
            "description": "Return eyes, lids, jaw, and head to neutral center.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "describe_features",
            "description": "Return a concise overview of Ivan's main conversation and robot features.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "feature_help",
            "description": "Explain one specific feature and how to use it well.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "feature": {"type": "STRING", "description": "Feature name such as intro, tracking, OCR, memory, or voice."},
                },
                "required": ["feature"],
            },
        },
        {
            "name": "gesture_head",
            "description": "Perform a nonverbal head gesture for yes or no.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "gesture": {"type": "STRING", "enum": ["yes", "no"]},
                },
                "required": ["gesture"],
            },
        },
        {
            "name": "read_visible_text",
            "description": "Read text, numbers, or simple math visible in the current camera frame using local OCR.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "mode": {
                        "type": "STRING",
                        "enum": ["auto", "document"],
                        "description": "Use document for centered paper, screens, whiteboards, or handwriting.",
                    }
                },
            },
        },
    ]
