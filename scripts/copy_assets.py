import shutil
import os

def copy_assets():
    src_dir = r"C:\Users\surya\.gemini\antigravity-ide\brain\e8abd1cc-3503-430a-8f8a-9aba31715183"
    dest_dir = r"c:\Users\surya\Desktop\crescendo_jail_break\assets"

    os.makedirs(dest_dir, exist_ok=True)

    mappings = {
        "project_architecture_9_phases_1783436978478.png": "architecture.png",
        "project_banner_9_phases_1783437038786.png": "banner.png",
        "project_risk_dynamics_1783434594175.png": "risk_dynamics.png"
    }

    print("Copying assets to project folder...")
    for src_name, dest_name in mappings.items():
        src_path = os.path.join(src_dir, src_name)
        dest_path = os.path.join(dest_dir, dest_name)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            print(f"Copied: {src_name} -> {dest_name}")
        else:
            print(f"Source file not found: {src_path}")
    print("Done!")

if __name__ == "__main__":
    copy_assets()
