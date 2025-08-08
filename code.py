import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- Database setup ---
conn = sqlite3.connect("ideas.db", check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    author_id INTEGER,
    date TEXT,
    votes INTEGER DEFAULT 0,
    FOREIGN KEY(author_id) REFERENCES users(id)
)
""")
conn.commit()

# --- Helper functions ---
def add_user(name, role):
    c.execute("INSERT INTO users (name, role) VALUES (?, ?)", (name, role))
    conn.commit()

def get_users():
    return c.execute("SELECT * FROM users").fetchall()

def add_idea(title, description, author_id):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO ideas (title, description, author_id, date) VALUES (?, ?, ?, ?)",
              (title, description, author_id, date_str))
    conn.commit()

def get_ideas():
    return pd.read_sql_query("""
        SELECT ideas.id, ideas.title, ideas.description, ideas.date, ideas.votes, users.name, users.role
        FROM ideas
        JOIN users ON ideas.author_id = users.id
        ORDER BY (CASE 
            WHEN users.role IN ('sergeant', 'expert', 'activist') THEN 1 ELSE 0 END) DESC,
            votes DESC
    """, conn)

def vote_idea(idea_id):
    c.execute("UPDATE ideas SET votes = votes + 1 WHERE id = ?", (idea_id,))
    conn.commit()

# --- UI ---
st.set_page_config(page_title="Palestine Ideas Platform", layout="centered")
st.title("🇵🇸 Palestine Ideas Platform")

menu = ["Add User", "Submit Idea", "View Ideas"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add User":
    st.subheader("Register as a User")
    name = st.text_input("Name")
    role = st.selectbox("Role", ["citizen", "sergeant", "expert", "activist"])
    if st.button("Register"):
        if name:
            add_user(name, role)
            st.success(f"User '{name}' registered as {role}")
        else:
            st.error("Please enter a name")

elif choice == "Submit Idea":
    st.subheader("Submit an Idea")
    users = get_users()
    if users:
        user_dict = {f"{u[1]} ({u[2]})": u[0] for u in users}
        selected_user = st.selectbox("Select Author", list(user_dict.keys()))
        title = st.text_input("Idea Title")
        description = st.text_area("Idea Description")
        if st.button("Submit Idea"):
            add_idea(title, description, user_dict[selected_user])
            st.success("Idea submitted successfully")
    else:
        st.warning("Please register a user first")

elif choice == "View Ideas":
    st.subheader("Ideas List")
    df = get_ideas()
    if not df.empty:
        for _, row in df.iterrows():
            st.markdown(f"### {row['title']} ({row['votes']} 👍)")
            st.markdown(f"**Author:** {row['name']} ({row['role']})")
            st.markdown(f"**Date:** {row['date']}")
            st.write(row["description"])
            if st.button(f"Vote for {row['id']}", key=row['id']):
                vote_idea(row['id'])
                st.rerun()
            st.markdown("---")
    else:
        st.info("No ideas yet.")
