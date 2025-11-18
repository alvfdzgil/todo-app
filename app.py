import streamlit as st
import json
import os
from datetime import datetime, date

DATA_DIR = "/app-data"
DATA_FILE = os.path.join(DATA_DIR, "todos.json")

# ----------------------------
# Utils: load / save
# ----------------------------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_todos():
    ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []

    # Soportar formato antiguo: lista de strings
    if isinstance(data, list) and (len(data) == 0 or isinstance(data[0], str)):
        todos = []
        for text in data:
            todos.append(
                {
                    "text": text,
                    "created_at": datetime.now().isoformat(timespec="minutes"),
                    "due_date": None,
                }
            )
        return todos

    # Se asume que ya es lista de diccionarios
    return data


def save_todos(todos):
    ensure_data_dir()
    with open(DATA_FILE, "w") as f:
        json.dump(todos, f, indent=2)


# ----------------------------
# App
# ----------------------------

st.set_page_config(page_title="TODO App", page_icon="✅", layout="centered")

st.title("✅ Simple TODO App (mejorada)")

st.caption("Gestor de tareas con fecha de creación, fecha límite y borrado.")

todos = load_todos()

st.markdown("### Añadir nueva tarea")

col_input, col_date, col_btn = st.columns([3, 2, 1])

with col_input:
    new_todo = st.text_input("Descripción", placeholder="Ej: Estudiar Docker")

with col_date:
    due_date = st.date_input(
        "Fecha límite",
        value=date.today(),
        help="Opcional, puedes dejar la fecha de hoy o cambiarla.",
    )

with col_btn:
    st.write("")  # Separador visual
    if st.button("➕ Añadir"):
        if new_todo.strip():
            todos.append(
                {
                    "text": new_todo.strip(),
                    "created_at": datetime.now().isoformat(timespec="minutes"),
                    "due_date": due_date.isoformat() if isinstance(due_date, date) else None,
                }
            )
            save_todos(todos)
            st.success("Tarea añadida.")
            st.rerun()
        else:
            st.warning("La descripción no puede estar vacía.")


st.markdown("---")
st.markdown("### Tus TODOs")

if not todos:
    st.info("No tienes tareas todavía. ¡Añade la primera arriba! 🙌")
else:
    # Ordenar por fecha límite (las más próximas primero), dejando las sin fecha al final
    def sort_key(t):
        if t.get("due_date"):
            return (0, t["due_date"])
        return (1, "")

    todos_sorted = sorted(todos, key=sort_key)

    # Mostrar en forma de “tabla” con botones de borrar
    for idx, todo in enumerate(todos_sorted):
        text = todo.get("text", "")
        created_at = todo.get("created_at", "")
        due = todo.get("due_date", None)

        # Parseo rápido de fechas para mostrar bonito
        try:
            created_str = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_str = created_at

        if due:
            try:
                due_str = datetime.fromisoformat(due).strftime("%Y-%m-%d")
                due_date_obj = datetime.fromisoformat(due).date()
            except Exception:
                due_str = due
                due_date_obj = None
        else:
            due_str = "—"
            due_date_obj = None

        overdue = False
        if due_date_obj and due_date_obj < date.today():
            overdue = True

        col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
        with col1:
            if overdue:
                st.markdown(f"**🔴 {text}**")
            else:
                st.markdown(f"**{text}**")

        with col2:
            st.caption(f"Creado: {created_str}")

        with col3:
            if overdue:
                st.caption(f"Vencía: **{due_str}**")
            else:
                st.caption(f"Vence: {due_str}")

        with col4:
            if st.button("🗑️", key=f"delete-{idx}"):
                # Buscar y eliminar el TODO exacto en la lista original
                # (por si hay varios con mismo texto)
                original_index = todos.index(todo)
                todos.pop(original_index)
                save_todos(todos)
                st.rerun()
