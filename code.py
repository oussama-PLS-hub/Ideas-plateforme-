import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Database setup (SQLite example)
engine = create_engine("sqlite:///ideas.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Example model
class Idea(Base):
    __tablename__ = "ideas"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(engine)

# Streamlit UI
st.set_page_config(page_title="Ideas Platform", layout="centered")
st.title("💡 Ideas Platform")

# Add new idea
st.header("Submit a new idea")
title = st.text_input("Title")
description = st.text_area("Description")
if st.button("Submit Idea"):
    if title and description:
        new_idea = Idea(title=title, description=description)
        session.add(new_idea)
        session.commit()
        st.success("Idea submitted successfully!")
    else:
        st.error("Please fill in all fields.")

# Display all ideas
st.header("All Ideas")
ideas = session.query(Idea).all()
for idea in ideas:
    st.subheader(idea.title)
    st.write(idea.description)
    st.caption(f"Submitted on: {idea.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
