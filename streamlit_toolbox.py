import os
import subprocess
import sys

import streamlit as st

from run_toolbox import TOOLS


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(script_rel_path: str):
    script_path = os.path.join(BASE_DIR, script_rel_path)
    if not os.path.exists(script_path):
        st.error(f"Script not found: {script_rel_path}")
        return

    st.write(f"Running `{script_rel_path}`")
    output_box = st.empty()
    output_box.code("Starting process...\n")

    process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []
    assert process.stdout is not None
    for line in process.stdout:
        output_lines.append(line.rstrip("\n"))
        output_box.code("\n".join(output_lines) or " ")

    return_code = process.wait()
    if return_code == 0:
        st.success("Completed successfully.")
    else:
        st.error(f"Script exited with code {return_code}.")


def main():
    st.set_page_config(page_title="Chorus Avery Toolbox", layout="wide")
    st.title("Chorus Avery Toolbox")
    st.caption("Run the same pipeline scripts currently exposed by launch.json.")

    st.info(
        "Some scripts are interactive and may wait for keyboard input in the "
        "process output area. Those scripts should be converted to CLI args "
        "for full GUI use."
    )

    selected_tool = st.selectbox(
        "Choose a tool",
        options=TOOLS,
        format_func=lambda tool: tool["name"],
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        run_clicked = st.button("Run Tool", type="primary")
    with col2:
        st.code(selected_tool["script"])

    if run_clicked:
        run_script(selected_tool["script"])


if __name__ == "__main__":
    main()
