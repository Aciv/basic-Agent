
from memory.memory import Message
from memory.skills_load import load_skills

def make_system_prompt(context_path, skills_dir):
    try:
        with open(context_path, "r", encoding="utf-8") as file:
            content = file.read()

    except Exception as e:
        print(f"load system context failed: {e}")
        content = ""
    

    skill_prompt = load_skills(skills_dir)


    system_message = Message(
        role="system",
        content="\n".join([content, skill_prompt])
    )


    return system_message

